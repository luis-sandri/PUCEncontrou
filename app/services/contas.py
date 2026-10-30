"""Gestão experimental de contas de Luís, sujeita à revisão de P09.

As escolhas de campos e limites deste módulo não aprovam regras de negócio.
Somente administradores ativos, confirmados no repositório, gerenciam contas.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol
import unicodedata

from werkzeug.security import generate_password_hash

from app.erros import ErroValidacao, PermissaoNegada
from app.models.conta import ContaAdministrativa, ContaAdministrativaPorta, Perfil
from app.repositories.sqlite_contas import RepositorioContasPorta


def _tem_controle(valor: str) -> bool:
    return any(unicodedata.category(caractere).startswith("C") for caractere in valor)


def normalizar_identificador(valor: object) -> str:
    """Identificador genérico; não presume um endereço de e-mail institucional."""
    if not isinstance(valor, str):
        raise ErroValidacao("Informe um identificador de login válido.")
    identificador = valor.strip().casefold()
    if (
        not 3 <= len(identificador) <= 120
        or any(caractere.isspace() for caractere in identificador)
        or _tem_controle(identificador)
    ):
        raise ErroValidacao("O identificador deve ter de 3 a 120 caracteres, sem espaços.")
    return identificador


def validar_nome(valor: object) -> str:
    if not isinstance(valor, str):
        raise ErroValidacao("Informe o nome da conta.")
    nome = valor.strip()
    if not 1 <= len(nome) <= 120 or _tem_controle(nome):
        raise ErroValidacao("O nome deve ter de 1 a 120 caracteres válidos.")
    return nome


def validar_senha(valor: object) -> str:
    """A senha permanece transitória e nunca é normalizada ou devolvida em DTOs."""
    if not isinstance(valor, str) or not 12 <= len(valor) <= 128:
        raise ErroValidacao("A senha deve ter de 12 a 128 caracteres.")
    try:
        valor.encode("utf-8")
    except UnicodeError:
        raise ErroValidacao("A senha deve conter caracteres Unicode válidos.") from None
    return valor


def validar_dados_conta(dados: Mapping[str, object]) -> dict[str, str]:
    if not isinstance(dados, Mapping) or set(dados) != {"nome", "identificador"}:
        raise ErroValidacao("Informe somente nome e identificador da conta.")
    return {
        "nome": validar_nome(dados["nome"]),
        "identificador": normalizar_identificador(dados["identificador"]),
    }


class GestaoContasPorta(Protocol):
    def listar_secretarios(
        self, *, ator: ContaAdministrativaPorta
    ) -> Sequence[ContaAdministrativaPorta]: ...

    def cadastrar_secretario(
        self,
        dados: Mapping[str, object],
        senha: str,
        *,
        ator: ContaAdministrativaPorta,
    ) -> ContaAdministrativaPorta: ...

    def gerenciar_secretario(
        self,
        conta_id: str,
        alteracoes: Mapping[str, object],
        *,
        ator: ContaAdministrativaPorta,
    ) -> ContaAdministrativaPorta: ...


class ServicoContas:
    """Aplica permissões e validação antes de qualquer gravação de contas."""

    def __init__(self, repositorio: RepositorioContasPorta) -> None:
        self._repositorio = repositorio

    def _exigir_administrador(self, ator: ContaAdministrativaPorta) -> None:
        conta_id = getattr(ator, "id", None)
        conta = (
            self._repositorio.buscar_por_id(conta_id)
            if isinstance(conta_id, str) and conta_id
            else None
        )
        if conta is None or not conta.ativa or conta.perfil != Perfil.ADMINISTRADOR:
            raise PermissaoNegada("A gestão de contas exige administrador ativo.")

    def listar_secretarios(
        self, *, ator: ContaAdministrativaPorta
    ) -> list[ContaAdministrativa]:
        self._exigir_administrador(ator)
        return self._repositorio.listar_secretarios()

    def cadastrar_secretario(
        self,
        dados: Mapping[str, object],
        senha: str,
        *,
        ator: ContaAdministrativaPorta,
    ) -> ContaAdministrativa:
        self._exigir_administrador(ator)
        dados_validados = validar_dados_conta(dados)
        senha_hash = generate_password_hash(validar_senha(senha))
        return self._repositorio.salvar_secretario(
            dados_validados, senha_hash=senha_hash
        )

    def gerenciar_secretario(
        self,
        conta_id: str,
        alteracoes: Mapping[str, object],
        *,
        ator: ContaAdministrativaPorta,
    ) -> ContaAdministrativa:
        self._exigir_administrador(ator)
        permitidos = {"nome", "identificador", "ativa", "senha"}
        if (
            not isinstance(alteracoes, Mapping)
            or not alteracoes
            or set(alteracoes) - permitidos
        ):
            raise ErroValidacao("Informe somente alterações permitidas para o secretário.")

        dados: dict[str, object] = {}
        if "nome" in alteracoes:
            dados["nome"] = validar_nome(alteracoes["nome"])
        if "identificador" in alteracoes:
            dados["identificador"] = normalizar_identificador(alteracoes["identificador"])
        if "ativa" in alteracoes:
            if alteracoes["ativa"] is not False:
                raise ErroValidacao("Esta versão permite somente desativar a conta.")
            dados["ativa"] = False
        senha_hash = None
        if "senha" in alteracoes:
            senha_hash = generate_password_hash(validar_senha(alteracoes["senha"]))
        return self._repositorio.atualizar_secretario(
            conta_id, dados, senha_hash=senha_hash
        )
