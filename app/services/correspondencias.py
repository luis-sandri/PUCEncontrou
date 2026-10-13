"""Esboço de André; critérios e pontuação ainda não foram aprovados."""

from collections.abc import Sequence
from typing import Protocol


class CandidatoCorrespondenciaPorta(Protocol):
    @property
    def ocorrencia_id(self) -> str: ...


class CorrespondenciasPorta(Protocol):
    def sugerir(self, ocorrencia_id: str) -> Sequence[CandidatoCorrespondenciaPorta]: ...
