"""Portas externas; a fronteira HTTP concreta de Luís está em atendimento_ocorrencias.

O núcleo de Marcelo mantém as operações de domínio. Entrada e autorização
são aplicadas antes de delegar lotes; não repassar request.form integralmente.
"""

from collections.abc import Iterable, Mapping
from typing import BinaryIO, Protocol

from app.models.conta import ContaAdministrativaPorta
from app.models.ocorrencia import OcorrenciaPorta, StatusOcorrencia


class LeituraOcorrenciasPorta(Protocol):
    """Dependência restrita para consultas e correspondências."""

    def obter(self, ocorrencia_id: str) -> OcorrenciaPorta: ...

    def listar(
        self, filtros: Mapping[str, object] | None = None
    ) -> Iterable[OcorrenciaPorta]: ...


class ServicoOcorrenciasPorta(LeituraOcorrenciasPorta, Protocol):
    def cadastrar(
        self, dados: Mapping[str, object], *, foto: BinaryIO | None
    ) -> OcorrenciaPorta: ...

    def editar(
        self,
        ocorrencia_id: str,
        dados: Mapping[str, object],
        *,
        ator: ContaAdministrativaPorta,
        foto: BinaryIO | None = None,
    ) -> OcorrenciaPorta: ...

    def excluir(
        self, ocorrencia_id: str, *, ator: ContaAdministrativaPorta, confirmacao: bool = False
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
