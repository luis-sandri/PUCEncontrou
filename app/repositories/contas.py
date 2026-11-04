"""Contrato de persistência de contas, independente da interface Flask."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from app.models.conta import ContaAdministrativa, ContaAdministrativaPorta, CredenciaisContaPorta


class RepositorioContasPorta(Protocol):
    def inicializar(self) -> None: ...

    def inicializar_administrador(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativa: ...

    def buscar_por_id(self, conta_id: str) -> CredenciaisContaPorta | None: ...

    def buscar_por_identificador(
        self, identificador: str
    ) -> CredenciaisContaPorta | None: ...

    def salvar_secretario(
        self, dados: Mapping[str, object], *, senha_hash: str
    ) -> ContaAdministrativaPorta: ...

    def listar_secretarios(self) -> list[ContaAdministrativa]: ...

    def atualizar_secretario(
        self,
        conta_id: str,
        dados: Mapping[str, object],
        *,
        senha_hash: str | None = None,
    ) -> ContaAdministrativa: ...

    def recuperar_administrador(
        self, identificador: str, *, senha_hash: str
    ) -> ContaAdministrativa: ...

    def importar_legado_sqlite(self, origem: Path | str) -> int: ...
