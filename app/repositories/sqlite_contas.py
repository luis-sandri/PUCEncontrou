"""Contrato privado de Luís; nenhum banco ou conta é criado nesta base."""

from collections.abc import Mapping
from typing import Protocol

from app.models.conta import ContaAdministrativaPorta, CredenciaisContaPorta


class RepositorioContasPorta(Protocol):
    def buscar_por_id(self, conta_id: str) -> CredenciaisContaPorta | None: ...

    def buscar_por_identificador(
        self, identificador: str
    ) -> CredenciaisContaPorta | None: ...

    def salvar_secretario(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativaPorta: ...
