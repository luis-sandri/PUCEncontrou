"""Gestão experimental de contas de Luís, sujeita à revisão de P09.

As escolhas de campos e limites deste módulo não aprovam regras de negócio.
Somente administradores ativos, confirmados no repositório, gerenciam contas.
"""

from collections.abc import Mapping, Sequence
import re
from typing import Protocol
import unicodedata

from werkzeug.security import generate_password_hash

from app.erros import ContaNaoEncontrada, ErroValidacao, PermissaoNegada
from app.models.conta import ContaAdministrativa, ContaAdministrativaPorta, Perfil
from app.repositories.contas import RepositorioContasPorta


def _tem_controle(valor: str) -> bool:
    return any(unicodedata.category(caractere).startswith("C") for caractere in valor)


def normalizar_identificador(valor: object) -> str:
    """E-mail institucional selecionado por Luís, normalizado para unicidade."""
    if not isinstance(valor, str):
        raise ErroValidacao("Informe um identificador de login válido.")
    identificador = valor.strip().casefold()
    if (
        len(identificador) > 120
        or re.fullmatch(r"[a-z0-9._%+\-]+@pucpr\.edu\.br", identificador) is None
        or identificador.startswith(".")
        or identificador.split("@")[0].endswith(".")
        or ".." in identificador
    ):
        raise ErroValidacao("Informe um e-mail institucional @pucpr.edu.br válido (até 120 caracteres).")
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
    def obter_secretario(
        self, conta_id: str, *, ator: ContaAdministrativaPorta
    ) -> ContaAdministrativaPorta: ...

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

    def obter_secretario(
        self, conta_id: str, *, ator: ContaAdministrativaPorta
    ) -> ContaAdministrativa:
        self._exigir_administrador(ator)
        conta = self._repositorio.buscar_por_id(conta_id)
        if conta is None or conta.perfil != Perfil.SECRETARIO:
            raise ContaNaoEncontrada("Conta de secretário não encontrada.")
        return conta.para_visao()

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
            if type(alteracoes["ativa"]) is not bool:
                raise ErroValidacao("Informe um estado de conta válido.")
            dados["ativa"] = alteracoes["ativa"]
        senha_hash = None
        if "senha" in alteracoes:
            senha_hash = generate_password_hash(validar_senha(alteracoes["senha"]))
        return self._repositorio.atualizar_secretario(
            conta_id, dados, senha_hash=senha_hash
        )
