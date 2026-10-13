"""Esboço técnico de Leandro: AVL manual como índice auxiliar de datas.

Não contém nós, rotações ou balanceamento implementados.
A classe concreta futura poderá se chamar ArvoreAVL.
"""

from collections.abc import Iterator
from datetime import date
from typing import Protocol


class IndiceDatasPorta(Protocol):
    def inserir(self, data: date, ocorrencia_id: str) -> None: ...

    def remover(self, data: date, ocorrencia_id: str) -> None: ...

    def buscar_periodo(self, inicio: date, fim: date) -> Iterator[str]: ...
