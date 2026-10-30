"""Persistência SQLite de contas e sessões do módulo experimental de Luís.

O construtor não acessa disco. A inicialização é uma ação explícita da CLI;
nenhuma conta ou senha padrão é criada.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Protocol
from uuid import uuid4

from app.erros import (
    ContaNaoEncontrada,
    ErroPersistencia,
    ErroValidacao,
    FalhaAutenticacao,
    IdentificadorEmUso,
)
from app.models.conta import (
    ContaAdministrativa,
    ContaAdministrativaPorta,
    CredenciaisConta,
    CredenciaisContaPorta,
    Perfil,
)


class RepositorioContasPorta(Protocol):
    def inicializar(self) -> None: ...

    def inicializar_administrador(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativa: ...

    def buscar_por_id(self, conta_id: str) -> CredenciaisContaPorta | None: ...

    def buscar_por_identificador(
        self, identificador: str
    ) -> CredenciaisContaPorta | None: ...

    def salvar_secretario(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativaPorta: ...

    def listar_secretarios(self) -> list[ContaAdministrativa]: ...

    def atualizar_secretario(
        self,
        conta_id: str,
        dados: Mapping[str, object],
        *,
        senha_hash: str | None = None,
    ) -> ContaAdministrativa: ...

    def criar_sessao(
        self, conta_id: str, token_hash: str, expira_em: int, *, senha_hash_esperada: str
    ) -> None: ...

    def buscar_sessao(
        self, token_hash: str, agora: int
    ) -> CredenciaisContaPorta | None: ...

    def revogar_sessao(self, token_hash: str) -> None: ...


class RepositorioContasSQLite:
    """Conexões curtas por operação, SQL parametrizado e transações de escrita."""

    def __init__(self, caminho: Path | str) -> None:
        self.caminho = Path(caminho)

    @contextmanager
    def _conexao(self, *, escrita: bool = False) -> Iterator[sqlite3.Connection]:
        conexao = None
        try:
            # mode=rw impede a criação silenciosa durante uma consulta.
            uri = self.caminho.resolve().as_uri() + "?mode=rw"
            conexao = sqlite3.connect(uri, uri=True, timeout=5)
            conexao.row_factory = sqlite3.Row
            conexao.execute("PRAGMA foreign_keys = ON")
            if conexao.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ErroPersistencia("Banco de contas não inicializado ou incompatível.")
            if escrita:
                conexao.execute("BEGIN IMMEDIATE")
            yield conexao
            if escrita:
                conexao.commit()
        except sqlite3.Error:
            raise ErroPersistencia("Não foi possível acessar o banco de contas.") from None
        finally:
            if conexao is not None:
                conexao.close()

    def inicializar(self) -> None:
        """Cria somente o esquema, preservando contas e recusando versão desconhecida."""
        conexao = None
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                descritor = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descritor)
            conexao = sqlite3.connect(self.caminho, timeout=5)
            conexao.execute("PRAGMA foreign_keys = ON")
            conexao.execute("BEGIN IMMEDIATE")
            versao = conexao.execute("PRAGMA user_version").fetchone()[0]
            if versao not in (0, 1):
                raise ErroPersistencia("Versão do banco de contas incompatível.")
            if versao == 0 and conexao.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone():
                raise ErroPersistencia("Banco existente sem versão reconhecida; inicialização recusada.")
            conexao.execute(
                """CREATE TABLE IF NOT EXISTS contas (
                    id TEXT PRIMARY KEY,
                    perfil TEXT NOT NULL CHECK (perfil IN ('SECRETARIO', 'ADMINISTRADOR')),
                    nome TEXT NOT NULL,
                    identificador TEXT NOT NULL UNIQUE,
                    ativa INTEGER NOT NULL CHECK (ativa IN (0, 1)),
                    senha_hash TEXT NOT NULL
                )"""
            )
            conexao.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS administrador_unico ON contas(perfil)
                WHERE perfil = 'ADMINISTRADOR'"""
            )
            conexao.execute(
                """CREATE TABLE IF NOT EXISTS sessoes (
                    token_hash TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
                    expira_em INTEGER NOT NULL
                )"""
            )
            conexao.execute(
                "CREATE INDEX IF NOT EXISTS sessoes_conta ON sessoes(conta_id)"
            )
            conexao.execute("PRAGMA user_version = 1")
            conexao.commit()
        except (sqlite3.Error, OSError):
            raise ErroPersistencia("Não foi possível inicializar o banco de contas.") from None
        finally:
            if conexao is not None:
                conexao.close()

    @staticmethod
    def _credenciais(registro: sqlite3.Row | None) -> CredenciaisConta | None:
        if registro is None:
            return None
        try:
            return CredenciaisConta(
                id=registro["id"],
                perfil=Perfil(registro["perfil"]),
                nome=registro["nome"],
                identificador=registro["identificador"],
                ativa=bool(registro["ativa"]),
                senha_hash=registro["senha_hash"],
            )
        except (ValueError, KeyError, IndexError):
            raise ErroPersistencia("Registro de conta inválido.") from None

    @staticmethod
    def _campos(dados: Mapping[str, object]) -> tuple[str, str]:
        nome, identificador = dados.get("nome"), dados.get("identificador")
        if not isinstance(nome, str) or not nome.strip():
            raise ErroValidacao("Informe o nome da conta.")
        if not isinstance(identificador, str) or not identificador.strip():
            raise ErroValidacao("Informe o identificador da conta.")
        return nome.strip(), identificador.strip().casefold()

    def buscar_por_id(self, conta_id: str) -> CredenciaisConta | None:
        with self._conexao() as conexao:
            return self._credenciais(
                conexao.execute("SELECT * FROM contas WHERE id = ?", (conta_id,)).fetchone()
            )

    def buscar_por_identificador(self, identificador: str) -> CredenciaisConta | None:
        with self._conexao() as conexao:
            return self._credenciais(
                conexao.execute(
                    "SELECT * FROM contas WHERE identificador = ?",
                    (identificador.strip().casefold(),),
                ).fetchone()
            )

    def _inserir(
        self,
        conexao: sqlite3.Connection,
        dados: Mapping[str, object],
        perfil: Perfil,
        senha_hash: str,
    ) -> ContaAdministrativa:
        nome, identificador = self._campos(dados)
        if not isinstance(senha_hash, str) or not senha_hash:
            raise ErroValidacao("Hash de senha ausente.")
        conta = ContaAdministrativa(str(uuid4()), perfil, nome, identificador, True)
        try:
            conexao.execute(
                "INSERT INTO contas (id, perfil, nome, identificador, ativa, senha_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conta.id, perfil.value, nome, identificador, 1, senha_hash),
            )
        except sqlite3.IntegrityError as erro:
            if getattr(erro, "sqlite_errorname", "") == "SQLITE_CONSTRAINT_UNIQUE":
                raise IdentificadorEmUso("Identificador já cadastrado.") from None
            raise
        return conta

    def salvar_secretario(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativa:
        with self._conexao(escrita=True) as conexao:
            return self._inserir(conexao, dados, Perfil.SECRETARIO, senha_hash)

    def inicializar_administrador(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativa:
        with self._conexao(escrita=True) as conexao:
            if conexao.execute(
                "SELECT 1 FROM contas WHERE perfil = ?", (Perfil.ADMINISTRADOR.value,)
            ).fetchone():
                raise ErroValidacao("A conta inicial de administrador já existe.")
            return self._inserir(conexao, dados, Perfil.ADMINISTRADOR, senha_hash)

    def listar_secretarios(self) -> list[ContaAdministrativa]:
        with self._conexao() as conexao:
            registros = conexao.execute(
                "SELECT * FROM contas WHERE perfil = ? ORDER BY identificador, id",
                (Perfil.SECRETARIO.value,),
            ).fetchall()
            return [self._credenciais(registro).para_visao() for registro in registros]

    def atualizar_secretario(
        self,
        conta_id: str,
        dados: Mapping[str, object],
        *,
        senha_hash: str | None = None,
    ) -> ContaAdministrativa:
        if set(dados) - {"nome", "identificador", "ativa"}:
            raise ErroValidacao("Campos de conta não permitidos.")
        if "ativa" in dados and not isinstance(dados["ativa"], bool):
            raise ErroValidacao("Estado da conta inválido.")
        if senha_hash is not None and (not isinstance(senha_hash, str) or not senha_hash):
            raise ErroValidacao("Hash de senha inválido.")
        with self._conexao(escrita=True) as conexao:
            credenciais = self._credenciais(conexao.execute(
                "SELECT * FROM contas WHERE id = ? AND perfil = ?",
                (conta_id, Perfil.SECRETARIO.value),
            ).fetchone())
            if credenciais is None:
                raise ContaNaoEncontrada("Conta de secretário não encontrada.")
            nome, identificador = self._campos({
                "nome": dados.get("nome", credenciais.nome),
                "identificador": dados.get("identificador", credenciais.identificador),
            })
            ativa = dados.get("ativa", credenciais.ativa)
            try:
                conexao.execute(
                    "UPDATE contas SET nome = ?, identificador = ?, ativa = ?, senha_hash = ? "
                    "WHERE id = ? AND perfil = ?",
                    (nome, identificador, int(ativa),
                     senha_hash if senha_hash is not None else credenciais.senha_hash,
                     conta_id, Perfil.SECRETARIO.value),
                )
            except sqlite3.IntegrityError as erro:
                if getattr(erro, "sqlite_errorname", "") == "SQLITE_CONSTRAINT_UNIQUE":
                    raise IdentificadorEmUso("Identificador já cadastrado.") from None
                raise
            if not ativa or senha_hash is not None or identificador != credenciais.identificador:
                conexao.execute("DELETE FROM sessoes WHERE conta_id = ?", (conta_id,))
            return ContaAdministrativa(
                conta_id, Perfil.SECRETARIO, nome, identificador, bool(ativa)
            )

    def criar_sessao(
        self, conta_id: str, token_hash: str, expira_em: int, *, senha_hash_esperada: str
    ) -> None:
        with self._conexao(escrita=True) as conexao:
            resultado = conexao.execute(
                "INSERT INTO sessoes (token_hash, conta_id, expira_em) "
                "SELECT ?, id, ? FROM contas WHERE id = ? AND ativa = 1 AND senha_hash = ?",
                (token_hash, expira_em, conta_id, senha_hash_esperada),
            )
            if resultado.rowcount != 1:
                raise FalhaAutenticacao("Não foi possível autenticar.")

    def buscar_sessao(self, token_hash: str, agora: int) -> CredenciaisConta | None:
        with self._conexao() as conexao:
            return self._credenciais(conexao.execute(
                "SELECT contas.* FROM contas JOIN sessoes ON contas.id = sessoes.conta_id "
                "WHERE sessoes.token_hash = ? AND sessoes.expira_em > ? AND contas.ativa = 1",
                (token_hash, agora),
            ).fetchone())

    def revogar_sessao(self, token_hash: str) -> None:
        with self._conexao(escrita=True) as conexao:
            conexao.execute("DELETE FROM sessoes WHERE token_hash = ?", (token_hash,))
