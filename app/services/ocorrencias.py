"""Esboço de CRUD e regras; Marcelo e Luís revisam antes da integração.

Mapping é temporário, até os campos e DTOs serem aprovados. Não autoriza
repassar request.form sem conversão e validação. Não há CRUD implementado.
"""

from collections.abc import Iterable, Mapping
from typing import Protocol

from app.models.conta import ContaAdministrativaPorta
from app.models.ocorrencia import OcorrenciaPorta, StatusOcorrencia


class LeituraOcorrenciasPorta(Protocol):
    """Dependência restrita para consultas e correspondências."""

    def obter(self, ocorrencia_id: str) -> OcorrenciaPorta: ...

    def listar(
        self, filtros: Mapping[str, object] | None = None
    ) -> Iterable[OcorrenciaPorta]: ...


class ServicoOcorrenciasPorta(LeituraOcorrenciasPorta, Protocol):
    def cadastrar(self, dados: Mapping[str, object]) -> OcorrenciaPorta: ...

    def editar(
        self,
        ocorrencia_id: str,
        dados: Mapping[str, object],
        *,
        ator: ContaAdministrativaPorta,
    ) -> OcorrenciaPorta: ...

    def excluir(
        self, ocorrencia_id: str, *, ator: ContaAdministrativaPorta
    ) -> None: ...

    def alterar_status(
        self,
        ocorrencia_id: str,
        novo_status: StatusOcorrencia,
        *,
        ator: ContaAdministrativaPorta,
        contexto: Mapping[str, object],
    ) -> Iterable[OcorrenciaPorta]: ...

    def vincular(
        self,
        perdido_id: str,
        encontrado_id: str,
        *,
        ator: ContaAdministrativaPorta,
    ) -> Iterable[OcorrenciaPorta]: ...
