"""Contas em JSON local, separadas das ocorrências de Matheus.

Sem cache ou criação no construtor. Um processo por arquivo; a CLI deve ser
usada com o servidor parado. O lock coordena as requisições desta instância.
"""

from collections.abc import Mapping
from contextlib import closing, suppress
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from uuid import uuid4

from app.erros import ContaNaoEncontrada, ErroPersistencia, ErroValidacao, IdentificadorEmUso
from app.models.conta import ContaAdministrativa, CredenciaisConta, Perfil


class RepositorioContasJSON:
    def __init__(self, caminho: Path | str) -> None:
        self.caminho = Path(caminho)
        self._lock = RLock()

    @staticmethod
    def _validar_registros(registros: object) -> list[CredenciaisConta]:
        campos = {"id", "perfil", "nome", "identificador", "ativa", "senha_hash", "versao_sessao"}
        if not isinstance(registros, list):
            raise ErroPersistencia("Formato do arquivo de contas inválido.")
        contas, ids, emails = [], set(), set()
        administradores = 0
        for registro in registros:
            if not isinstance(registro, dict) or set(registro) != campos:
                raise ErroPersistencia("Registro de conta inválido.")
            for campo in ("id", "nome", "identificador", "senha_hash"):
                valor = registro[campo]
                if not isinstance(valor, str) or not valor.strip():
                    raise ErroPersistencia("Registro de conta inválido.")
                try:
                    valor.encode("utf-8")
                except UnicodeError:
                    raise ErroPersistencia("Registro de conta inválido.") from None
            email = registro["identificador"]
            if (type(registro["ativa"]) is not bool
                    or type(registro["versao_sessao"]) is not int
                    or registro["versao_sessao"] < 0
                    or email != email.strip().casefold()
                    or registro["id"] in ids or email in emails):
                raise ErroPersistencia("Arquivo de contas contém dados inválidos ou duplicados.")
            try:
                perfil = Perfil(registro["perfil"])
            except (TypeError, ValueError):
                raise ErroPersistencia("Perfil de conta inválido.") from None
            administradores += perfil is Perfil.ADMINISTRADOR
            if administradores > 1:
                raise ErroPersistencia("Arquivo de contas contém mais de um administrador inicial.")
            ids.add(registro["id"])
            emails.add(email)
            contas.append(CredenciaisConta(**{**registro, "perfil": perfil}))
        return contas

    def _carregar(self) -> list[CredenciaisConta]:
        try:
            with self.caminho.open(encoding="utf-8") as arquivo:
                documento = json.load(arquivo)
        except (OSError, UnicodeError, ValueError):
            raise ErroPersistencia("Não foi possível ler o arquivo de contas.") from None
        if (not isinstance(documento, dict) or set(documento) != {"versao", "contas"}
                or type(documento["versao"]) is not int or documento["versao"] != 1):
            raise ErroPersistencia("Versão ou formato do arquivo de contas incompatível.")
        return self._validar_registros(documento["contas"])

    def _gravar(self, contas: list[CredenciaisConta]) -> None:
        registros = [{**asdict(conta), "perfil": conta.perfil.value} for conta in contas]
        self._validar_registros(registros)
        temporario = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.caminho.parent,
                prefix=".contas-", suffix=".tmp", delete=False,
            ) as arquivo:
                temporario = Path(arquivo.name)
                json.dump({"versao": 1, "contas": registros}, arquivo, ensure_ascii=False, indent=2)
                arquivo.write("\n")
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, self.caminho)
        except (OSError, UnicodeError, ValueError):
            raise ErroPersistencia("Não foi possível salvar o arquivo de contas.") from None
        finally:
            if temporario is not None:
                with suppress(OSError):
                    temporario.unlink(missing_ok=True)

    def inicializar(self) -> None:
        """Cria somente arquivo vazio; arquivo existente inválido nunca é substituído."""
        with self._lock:
            if self.caminho.exists():
                self._carregar()
                return
            try:
                self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError:
                raise ErroPersistencia("Não foi possível preparar o arquivo de contas.") from None
            self._gravar([])

    def buscar_por_id(self, conta_id: str) -> CredenciaisConta | None:
        with self._lock:
            return next((conta for conta in self._carregar() if conta.id == conta_id), None)

    def buscar_por_identificador(self, identificador: str) -> CredenciaisConta | None:
        email = identificador.strip().casefold()
        with self._lock:
            return next((conta for conta in self._carregar() if conta.identificador == email), None)

    def listar_secretarios(self) -> list[ContaAdministrativa]:
        with self._lock:
            contas = sorted(self._carregar(), key=lambda conta: (conta.identificador, conta.id))
            return [conta.para_visao() for conta in contas if conta.perfil is Perfil.SECRETARIO]

    @staticmethod
    def _campos(dados: Mapping[str, object]) -> tuple[str, str]:
        nome, identificador = dados.get("nome"), dados.get("identificador")
        if not isinstance(nome, str) or not nome.strip():
            raise ErroValidacao("Informe o nome da conta.")
        if not isinstance(identificador, str) or not identificador.strip():
            raise ErroValidacao("Informe o e-mail da conta.")
        return nome.strip(), identificador.strip().casefold()

    @staticmethod
    def _email_livre(contas: list[CredenciaisConta], email: str, *, exceto: str | None = None) -> None:
        if any(conta.identificador == email and conta.id != exceto for conta in contas):
            raise IdentificadorEmUso("E-mail já cadastrado.")

    def _inserir(self, dados: Mapping[str, object], senha_hash: str, perfil: Perfil) -> ContaAdministrativa:
        nome, email = self._campos(dados)
        if not isinstance(senha_hash, str) or not senha_hash:
            raise ErroValidacao("Hash de senha ausente.")
        with self._lock:
            contas = self._carregar()
            if perfil is Perfil.ADMINISTRADOR and any(c.perfil is perfil for c in contas):
                raise ErroValidacao("A conta inicial de administrador já existe.")
            self._email_livre(contas, email)
            nova = CredenciaisConta(str(uuid4()), perfil, nome, email, True, senha_hash)
            self._gravar([*contas, nova])
            return nova.para_visao()

    def salvar_secretario(self, dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativa:
        return self._inserir(dados, senha_hash, Perfil.SECRETARIO)

    def inicializar_administrador(self, dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativa:
        return self._inserir(dados, senha_hash, Perfil.ADMINISTRADOR)

    def atualizar_secretario(
        self, conta_id: str, dados: Mapping[str, object], *, senha_hash: str | None = None,
    ) -> ContaAdministrativa:
        if set(dados) - {"nome", "identificador", "ativa"}:
            raise ErroValidacao("Campos de conta não permitidos.")
        if "ativa" in dados and type(dados["ativa"]) is not bool:
            raise ErroValidacao("Estado da conta inválido.")
        if senha_hash is not None and (not isinstance(senha_hash, str) or not senha_hash):
            raise ErroValidacao("Hash de senha inválido.")
        with self._lock:
            contas = self._carregar()
            for indice, conta in enumerate(contas):
                if conta.id == conta_id and conta.perfil is Perfil.SECRETARIO:
                    nome, email = self._campos({
                        "nome": dados.get("nome", conta.nome),
                        "identificador": dados.get("identificador", conta.identificador),
                    })
                    self._email_livre(contas, email, exceto=conta_id)
                    ativa = dados.get("ativa", conta.ativa)
                    invalidar = ativa != conta.ativa or email != conta.identificador or senha_hash is not None
                    nova = replace(
                        conta, nome=nome, identificador=email, ativa=ativa,
                        senha_hash=senha_hash if senha_hash is not None else conta.senha_hash,
                        versao_sessao=conta.versao_sessao + int(invalidar),
                    )
                    contas[indice] = nova
                    self._gravar(contas)
                    return nova.para_visao()
            raise ContaNaoEncontrada("Conta de secretário não encontrada.")

    def recuperar_administrador(self, identificador: str, *, senha_hash: str) -> ContaAdministrativa:
        with self._lock:
            contas = self._carregar()
            for indice, conta in enumerate(contas):
                if conta.perfil is Perfil.ADMINISTRADOR:
                    self._email_livre(contas, identificador, exceto=conta.id)
                    nova = replace(
                        conta, identificador=identificador, senha_hash=senha_hash,
                        ativa=True, versao_sessao=conta.versao_sessao + 1,
                    )
                    contas[indice] = nova
                    self._gravar(contas)
                    return nova.para_visao()
            raise ContaNaoEncontrada("Administrador inicial não encontrado.")

    def importar_legado_sqlite(self, origem: Path | str) -> int:
        """Conversão explícita do protótipo anterior; SQLite é aberto só para leitura."""
        import sqlite3

        with self._lock:
            if self.caminho.exists():
                raise ErroValidacao("O arquivo JSON de contas já existe; importação recusada.")
            try:
                uri = Path(origem).resolve().as_uri() + "?mode=ro"
                with closing(sqlite3.connect(uri, uri=True)) as con:
                    con.row_factory = sqlite3.Row
                    versao = con.execute("PRAGMA user_version").fetchone()[0]
                    if versao not in (1, 2):
                        raise ErroPersistencia("Versão do legado de contas incompatível.")
                    registros = []
                    for linha in con.execute("SELECT * FROM contas"):
                        if linha["ativa"] not in (0, 1):
                            raise ErroPersistencia("Registro legado inválido.")
                        registros.append({
                            "id": linha["id"], "perfil": linha["perfil"], "nome": linha["nome"],
                            "identificador": linha["identificador"].strip().casefold(),
                            "ativa": bool(linha["ativa"]), "senha_hash": linha["senha_hash"],
                            "versao_sessao": linha["versao_sessao"] if versao == 2 else 0,
                        })
                contas = self._validar_registros(registros)
                self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except (sqlite3.Error, OSError, KeyError, IndexError, AttributeError):
                raise ErroPersistencia("Não foi possível importar o legado de contas.") from None
            self._gravar(contas)
            return len(contas)
