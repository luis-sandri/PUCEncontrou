"""Esboço de Leandro: resolve IDs da AVL para registros da Lista via serviço."""

from collections.abc import Iterable
from datetime import date
from typing import Protocol

from app.models.ocorrencia import OcorrenciaPorta


class ConsultaPeriodoPorta(Protocol):
    def buscar_periodo(
        self, inicio: date, fim: date
    ) -> Iterable[OcorrenciaPorta]: ...
