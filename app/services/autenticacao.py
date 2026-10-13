"""Esboço de Luís. Nenhuma senha, sessão ou autorização implementada."""

from typing import Protocol

from app.models.conta import ContaAdministrativaPorta


class AutenticacaoPorta(Protocol):
    def autenticar(
        self, identificador: str, senha: str
    ) -> ContaAdministrativaPorta: ...
