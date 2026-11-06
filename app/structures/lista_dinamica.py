"""Lista genérica com buffer fixo, expansão e deslocamento manuais.

A list Python serve somente para alocar o buffer [None] * capacidade.
Nenhuma operação pronta de inserção, remoção ou crescimento é usada nele.
"""

from collections.abc import Callable, Iterator
from typing import Generic, Protocol, TypeVar, cast

T = TypeVar("T")


class ListaDinamicaPorta(Protocol[T]):
    def inserir(self, item: T) -> None: ...

    def obter(self, indice: int) -> T: ...

    def atualizar(self, indice: int, item: T) -> None: ...

    def remover(self, indice: int) -> T: ...

    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator[T]: ...


class ListaDinamica(Generic[T]):
    """Armazena elementos nas posições 0 até tamanho-1, em ordem de inserção.

    Não conhece ocorrências, usuários ou persistência. O serviço fornece
    objetos validados e decide qual posição corrigir ou excluir. Os índices
    são posições temporárias, nunca identificadores dos objetos.
    """

    def __init__(self, capacidade_inicial: int = 4) -> None:
        if type(capacidade_inicial) is not int:
            raise TypeError("A capacidade inicial deve ser um número inteiro.")
        if capacidade_inicial < 1:
            raise ValueError("A capacidade inicial deve ser positiva.")
        self._capacidade = capacidade_inicial
        self._dados: list[T | None] = [None] * capacidade_inicial
        self._tamanho = 0
        self._versao = 0

    @property
    def capacidade(self) -> int:
        """Quantidade de posições alocadas; não é a quantidade de registros."""
        return self._capacidade

    def __len__(self) -> int:
        return self._tamanho

    def inserir(self, item: T) -> None:
        """Insere no final. Custo amortizado O(1); expansão custa O(n)."""
        if self._tamanho == self._capacidade:
            self._expandir()
        self._dados[self._tamanho] = item
        self._tamanho += 1
        self._versao += 1

    def obter(self, indice: int) -> T:
        self._validar_indice(indice)
        # None também pode ser um elemento legítimo; tamanho delimita ocupação.
        return cast(T, self._dados[indice])

    def atualizar(self, indice: int, item: T) -> None:
        """Substitui uma posição em O(1), sem inserir ou trocar a ordem."""
        self._validar_indice(indice)
        self._dados[indice] = item
        self._versao += 1

    def remover(self, indice: int) -> T:
        """Remove e desloca manualmente os sucessores para a esquerda, O(n)."""
        self._validar_indice(indice)
        removido = cast(T, self._dados[indice])
        for posicao in range(indice, self._tamanho - 1):
            self._dados[posicao] = self._dados[posicao + 1]
        self._tamanho -= 1
        self._dados[self._tamanho] = None
        self._versao += 1
        return removido

    def buscar_indice(self, predicado: Callable[[T], bool]) -> int | None:
        """Busca sequencial: primeira posição que satisfaz o predicado, O(n)."""
        self._validar_predicado(predicado)
        versao = self._versao
        for indice, item in enumerate(self):
            corresponde = bool(predicado(item))
            self._validar_versao(versao)
            if corresponde:
                return indice
        return None

    def buscar(self, predicado: Callable[[T], bool]) -> T | None:
        """Retorna a primeira correspondência, ou None quando não encontra."""
        indice = self.buscar_indice(predicado)
        return None if indice is None else self.obter(indice)

    def filtrar(self, predicado: Callable[[T], bool]) -> "ListaDinamica[T]":
        """Produz outra Lista manual em O(n), preservando origem e ordem.

        Compartilha as referências dos elementos, sem copiar seu conteúdo.
        Objetos Ocorrencia são imutáveis; outros tipos seguem sua própria regra.
        """
        self._validar_predicado(predicado)
        resultado = ListaDinamica[T]()
        for item in self:
            if predicado(item):
                resultado.inserir(item)
        return resultado

    def __iter__(self) -> Iterator[T]:
        # Captura a versão no iter(), não apenas quando o primeiro next ocorrer.
        return self._percorrer(self._versao)

    def _percorrer(self, versao: int) -> Iterator[T]:
        for indice in range(self._tamanho):
            self._validar_versao(versao)
            yield cast(T, self._dados[indice])
        self._validar_versao(versao)

    def _expandir(self) -> None:
        nova_capacidade = self._capacidade * 2
        novos_dados: list[T | None] = [None] * nova_capacidade
        for indice in range(self._tamanho):
            novos_dados[indice] = self._dados[indice]
        self._dados = novos_dados
        self._capacidade = nova_capacidade

    def _validar_indice(self, indice: int) -> None:
        if type(indice) is not int:
            raise TypeError("O índice deve ser um número inteiro.")
        if indice < 0 or indice >= self._tamanho:
            raise IndexError("Índice fora das posições ocupadas da Lista.")

    def _validar_versao(self, versao: int) -> None:
        if versao != self._versao:
            raise RuntimeError("A Lista foi alterada durante o percorrimento.")

    @staticmethod
    def _validar_predicado(predicado: Callable[[T], bool]) -> None:
        if not callable(predicado):
            raise TypeError("Informe uma função como predicado.")
