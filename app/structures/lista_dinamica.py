"""Esboço técnico de Marcelo: array, capacidade e redimensionamento manuais.

O protocolo não contém implementação e não cumpre o requisito acadêmico.
A classe concreta futura poderá se chamar ListaDinamica.
"""

from collections.abc import Iterator
from typing import Protocol, TypeVar

T = TypeVar("T")


class ListaDinamicaPorta(Protocol[T]):
    def inserir(self, item: T) -> None: ...

    def obter(self, indice: int) -> T: ...

    def atualizar(self, indice: int, item: T) -> None: ...

    def remover(self, indice: int) -> T: ...

    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator[T]: ...
