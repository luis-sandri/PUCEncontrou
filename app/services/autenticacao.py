"""Autenticação simples: o Flask mantém a sessão e o serviço consulta a conta."""

from collections.abc import Mapping
import secrets
from typing import Protocol

from werkzeug.security import check_password_hash, generate_password_hash

from app.erros import ErroValidacao, FalhaAutenticacao
from app.models.conta import ContaAdministrativa, ContaAdministrativaPorta
from app.repositories.sqlite_contas import RepositorioContasPorta
from app.services.contas import normalizar_identificador, validar_dados_conta, validar_senha


class AutenticacaoPorta(Protocol):
    def autenticar(
        self, identificador: str, senha: str
    ) -> ContaAdministrativaPorta: ...

    def obter_sessao(
        self, conta_id: str, versao_sessao: int
    ) -> ContaAdministrativaPorta | None: ...


class ServicoAutenticacao:
    """Não conhece cookies nem Flask; devolve somente a visão sem senha."""

    def __init__(self, repositorio: RepositorioContasPorta) -> None:
        self._repositorio = repositorio
        self._hash_ficticio = generate_password_hash(secrets.token_urlsafe(32))

    def autenticar(self, identificador: str, senha: str) -> ContaAdministrativa:
        try:
            email = normalizar_identificador(identificador)
        except ErroValidacao:
            email = None
        conta = self._repositorio.buscar_por_identificador(email) if email else None
        senha_hash = conta.senha_hash if conta is not None else self._hash_ficticio
        senha_valida = isinstance(senha, str) and 12 <= len(senha) <= 128
        try:
            corresponde = check_password_hash(senha_hash, senha if senha_valida else "")
        except (ValueError, TypeError):
            corresponde = False
        if conta is None or not conta.ativa or not senha_valida or not corresponde:
            raise FalhaAutenticacao("E-mail ou senha inválidos.")
        return conta.para_visao()

    def obter_sessao(
        self, conta_id: str, versao_sessao: int
    ) -> ContaAdministrativa | None:
        if not isinstance(conta_id, str) or type(versao_sessao) is not int:
            return None
        conta = self._repositorio.buscar_por_id(conta_id)
        if conta is None or not conta.ativa or conta.versao_sessao != versao_sessao:
            return None
        return conta.para_visao()

    def atualizar_banco(self) -> None:
        """Somente CLI: cria ou migra o esquema sem criar contas."""
        self._repositorio.inicializar()

    def inicializar_administrador(
        self, dados: Mapping[str, object], senha: str
    ) -> ContaAdministrativa:
        dados_validados = validar_dados_conta(dados)
        senha_hash = generate_password_hash(validar_senha(senha))
        self.atualizar_banco()
        return self._repositorio.inicializar_administrador(dados_validados, senha_hash=senha_hash)

    def recuperar_administrador(self, identificador: str, senha: str) -> ContaAdministrativa:
        """Recuperação por operador local; não expor como rota pública."""
        email = normalizar_identificador(identificador)
        senha_hash = generate_password_hash(validar_senha(senha))
        self.atualizar_banco()
        return self._repositorio.recuperar_administrador(email, senha_hash=senha_hash)
