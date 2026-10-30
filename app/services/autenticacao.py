"""Autenticação e sessões experimentais para revisão de P09/P10."""

from collections.abc import Mapping
import hashlib
import re
import secrets
import time
from typing import Protocol

from werkzeug.security import check_password_hash, generate_password_hash

from app.erros import ErroValidacao, FalhaAutenticacao
from app.models.conta import (
    ContaAdministrativa,
    ContaAdministrativaPorta,
    CredenciaisContaPorta,
)
from app.repositories.sqlite_contas import RepositorioContasPorta
from app.services.contas import (
    normalizar_identificador,
    validar_dados_conta,
    validar_senha,
)

_PADRAO_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_MENSAGEM_FALHA = "Identificador ou senha inválidos."


class AutenticacaoPorta(Protocol):
    def autenticar(
        self, identificador: str, senha: str
    ) -> ContaAdministrativaPorta: ...

    def iniciar_sessao(
        self, identificador: str, senha: str
    ) -> tuple[ContaAdministrativaPorta, str]: ...

    def obter_sessao(self, token: str) -> ContaAdministrativaPorta | None: ...

    def encerrar_sessao(self, token: str) -> None: ...


class ServicoAutenticacao:
    """Não recebe Flask nem entrega credenciais privadas aos consumidores."""

    def __init__(
        self,
        repositorio: RepositorioContasPorta,
        duracao_sessao_segundos: int = 1800,
    ) -> None:
        if type(duracao_sessao_segundos) is not int or duracao_sessao_segundos <= 0:
            raise ValueError("A duração da sessão deve ser um inteiro positivo.")
        self._repositorio = repositorio
        self._duracao_sessao_segundos = duracao_sessao_segundos
        # Custo de verificação também quando o login não existe, sem senha padrão.
        self._hash_ficticio = generate_password_hash(secrets.token_urlsafe(32))

    def _autenticar_credenciais(
        self, identificador: str, senha: str
    ) -> CredenciaisContaPorta:
        try:
            identificador_normalizado = normalizar_identificador(identificador)
        except ErroValidacao:
            identificador_normalizado = None
        senha_valida = isinstance(senha, str) and 12 <= len(senha) <= 128
        conta = (
            self._repositorio.buscar_por_identificador(identificador_normalizado)
            if identificador_normalizado is not None
            else None
        )
        senha_hash = conta.senha_hash if conta is not None else self._hash_ficticio
        try:
            corresponde = check_password_hash(senha_hash, senha if senha_valida else "")
        except (ValueError, TypeError):
            corresponde = False
        if conta is None or not conta.ativa or not senha_valida or not corresponde:
            raise FalhaAutenticacao(_MENSAGEM_FALHA)
        return conta

    @staticmethod
    def _para_visao(conta: CredenciaisContaPorta) -> ContaAdministrativa:
        return ContaAdministrativa(
            id=conta.id,
            perfil=conta.perfil,
            nome=conta.nome,
            identificador=conta.identificador,
            ativa=conta.ativa,
        )

    def autenticar(self, identificador: str, senha: str) -> ContaAdministrativa:
        return self._para_visao(self._autenticar_credenciais(identificador, senha))

    def iniciar_sessao(
        self, identificador: str, senha: str
    ) -> tuple[ContaAdministrativa, str]:
        credenciais = self._autenticar_credenciais(identificador, senha)
        token = secrets.token_urlsafe(32)
        self._repositorio.criar_sessao(
            credenciais.id,
            self._hash_token(token),
            int(time.time()) + self._duracao_sessao_segundos,
            senha_hash_esperada=credenciais.senha_hash,
        )
        return self._para_visao(credenciais), token

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    @staticmethod
    def _token_valido(token: object) -> bool:
        return isinstance(token, str) and _PADRAO_TOKEN.fullmatch(token) is not None

    def obter_sessao(self, token: str) -> ContaAdministrativa | None:
        if not self._token_valido(token):
            return None
        conta = self._repositorio.buscar_sessao(self._hash_token(token), int(time.time()))
        if conta is None:
            return None
        return self._para_visao(conta)

    def encerrar_sessao(self, token: str) -> None:
        if self._token_valido(token):
            self._repositorio.revogar_sessao(self._hash_token(token))

    def inicializar_administrador(
        self, dados: Mapping[str, object], senha: str
    ) -> ContaAdministrativa:
        """Apenas para bootstrap por CLI local; não deve ser exposto como rota."""
        dados_validados = validar_dados_conta(dados)
        senha_hash = generate_password_hash(validar_senha(senha))
        self._repositorio.inicializar()
        return self._repositorio.inicializar_administrador(
            dados_validados, senha_hash=senha_hash
        )
