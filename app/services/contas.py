"""Esboço de Luís; gestão somente por administrador, sem operações concretas."""

from collections.abc import Mapping
from typing import Protocol

from app.models.conta import ContaAdministrativaPorta


class GestaoContasPorta(Protocol):
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
