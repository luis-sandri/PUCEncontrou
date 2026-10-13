"""Perfis aprovados; contratos de contas a serem implementados por Luís."""

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


class CredenciaisContaPorta(ContaAdministrativaPorta, Protocol):
    """Visão privada do repositório para autenticação; nunca para templates."""

    @property
    def senha_hash(self) -> str: ...
