"""Perfis aprovados e objetos imutáveis da implementação experimental de contas."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class Perfil(str, Enum):
    SECRETARIO = "SECRETARIO"
    ADMINISTRADOR = "ADMINISTRADOR"


class ContaAdministrativaPorta(Protocol):
    """Visão sem credenciais para serviços; identificador opaco proposto."""

    @property
    def id(self) -> str: ...

    @property
    def perfil(self) -> Perfil: ...

    @property
    def nome(self) -> str: ...

    @property
    def identificador(self) -> str: ...

    @property
    def ativa(self) -> bool: ...


class CredenciaisContaPorta(ContaAdministrativaPorta, Protocol):
    """Visão privada do repositório para autenticação; nunca para templates."""

    @property
    def senha_hash(self) -> str: ...

    def para_visao(self) -> "ContaAdministrativa": ...


@dataclass(frozen=True, slots=True)
class ContaAdministrativa:
    """Visão administrativa sem hash, segura para projeção explícita nas rotas."""

    id: str
    perfil: Perfil
    nome: str
    identificador: str
    ativa: bool


@dataclass(frozen=True, slots=True)
class CredenciaisConta:
    """Objeto privado do repositório/autenticação; não enviar para a interface."""

    id: str
    perfil: Perfil
    nome: str
    identificador: str
    ativa: bool
    senha_hash: str = field(repr=False)

    def para_visao(self) -> ContaAdministrativa:
        return ContaAdministrativa(
            id=self.id,
            perfil=self.perfil,
            nome=self.nome,
            identificador=self.identificador,
            ativa=self.ativa,
        )
