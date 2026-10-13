"""Contrato de Matheus. Formato JSON e serialização aguardam o modelo."""

from collections.abc import Iterable
from typing import Protocol

from app.models.ocorrencia import OcorrenciaPorta


class RepositorioOcorrenciasPorta(Protocol):
    def carregar(self) -> Iterable[OcorrenciaPorta]: ...

    def salvar(self, ocorrencias: Iterable[OcorrenciaPorta]) -> None: ...
