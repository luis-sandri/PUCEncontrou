"""Esboço de Leandro: resolve IDs da AVL para registros da Lista via serviço."""

from collections.abc import Callable, Iterable
from datetime import date
from typing import Protocol

from app.erros import ErroValidacao
from app.models.ocorrencia import OcorrenciaPorta
from app.structures.avl import IndiceDatasPorta


class ConsultaPeriodoPorta(Protocol):
    def buscar_periodo(
        self, inicio: date, fim: date
    ) -> Iterable[OcorrenciaPorta]: ...


class ServicoConsultaPeriodo:
    """Implementação da consulta temporal delegando a busca de IDs ao índice AVL manual."""

    def __init__(
        self,
        indice: IndiceDatasPorta,
        obter: Callable[[str], OcorrenciaPorta | None],
    ) -> None:
        self._indice = indice
        self._obter = obter

    def buscar_periodo(self, inicio: date, fim: date) -> tuple[OcorrenciaPorta, ...]:
        if inicio > fim:
            raise ErroValidacao("A data de início deve ser anterior ou igual à data de fim.")
        itens = []
        for ocorrencia_id in self._indice.buscar_periodo(inicio, fim):
            ocorrencia = self._obter(ocorrencia_id)
            if ocorrencia is not None:
                itens.append(ocorrencia)
        return tuple(itens)
