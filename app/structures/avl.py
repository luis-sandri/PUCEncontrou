"""Esboço técnico de Leandro: AVL manual como índice auxiliar de datas.

Não contém nós, rotações ou balanceamento implementados.
A classe concreta futura poderá se chamar ArvoreAVL.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol


class IndiceDatasPorta(Protocol):
    def inserir(self, data: date, ocorrencia_id: str) -> None: ...

    def remover(self, data: date, ocorrencia_id: str) -> None: ...

    def buscar_periodo(self, inicio: date, fim: date) -> Iterator[str]: ...


@dataclass
class _NoAVL:
    """Nó interno da árvore AVL com chave composta (data, ocorrencia_id)."""

    data: date
    ocorrencia_id: str
    esquerda: "_NoAVL | None" = None
    direita: "_NoAVL | None" = None
    altura: int = 1

    @property
    def chave(self) -> tuple[date, str]:
        return (self.data, self.ocorrencia_id)


class ArvoreAVL:
    """Índice temporal manual baseado em árvore AVL com chave composta (data, id)."""

    def __init__(self) -> None:
        self._raiz: _NoAVL | None = None
        self._tamanho: int = 0

    def __len__(self) -> int:
        return self._tamanho

    def inserir(self, data: date, ocorrencia_id: str) -> None:
        self._raiz, inserido = self._inserir_recursivo(
            self._raiz, data, ocorrencia_id
        )
        if inserido:
            self._tamanho += 1

    def remover(self, data: date, ocorrencia_id: str) -> None:
        chave = (data, ocorrencia_id)
        self._raiz, removido = self._remover_recursivo(self._raiz, chave)
        if removido:
            self._tamanho -= 1

    def buscar_periodo(self, inicio: date, fim: date) -> Iterator[str]:
        if inicio > fim:
            raise ValueError(
                "A data de início não pode ser maior que a data de fim."
            )
        return self._buscar_periodo_recursivo(self._raiz, inicio, fim)

    def _altura(self, no: _NoAVL | None) -> int:
        return no.altura if no is not None else 0

    def _atualizar_altura(self, no: _NoAVL) -> None:
        altura_esq = self._altura(no.esquerda)
        altura_dir = self._altura(no.direita)
        no.altura = 1 + (altura_esq if altura_esq > altura_dir else altura_dir)

    def _fator_balanceamento(self, no: _NoAVL | None) -> int:
        if no is None:
            return 0
        return self._altura(no.esquerda) - self._altura(no.direita)

    def _rotacao_direita(self, desbalanceado: _NoAVL) -> _NoAVL:
        nova_raiz = desbalanceado.esquerda
        if nova_raiz is None:
            return desbalanceado

        subarvore_transferida = nova_raiz.direita
        nova_raiz.direita = desbalanceado
        desbalanceado.esquerda = subarvore_transferida

        self._atualizar_altura(desbalanceado)
        self._atualizar_altura(nova_raiz)
        return nova_raiz

    def _rotacao_esquerda(self, desbalanceado: _NoAVL) -> _NoAVL:
        nova_raiz = desbalanceado.direita
        if nova_raiz is None:
            return desbalanceado

        subarvore_transferida = nova_raiz.esquerda
        nova_raiz.esquerda = desbalanceado
        desbalanceado.direita = subarvore_transferida

        self._atualizar_altura(desbalanceado)
        self._atualizar_altura(nova_raiz)
        return nova_raiz

    def _rebalancear(self, no: _NoAVL) -> _NoAVL:
        self._atualizar_altura(no)
        fator = self._fator_balanceamento(no)

        # Caso Esquerda-Esquerda (LL) ou Esquerda-Direita (LR)
        if fator > 1:
            if self._fator_balanceamento(no.esquerda) < 0 and no.esquerda is not None:
                no.esquerda = self._rotacao_esquerda(no.esquerda)
            return self._rotacao_direita(no)

        # Caso Direita-Direita (RR) ou Direita-Esquerda (RL)
        if fator < -1:
            if self._fator_balanceamento(no.direita) > 0 and no.direita is not None:
                no.direita = self._rotacao_direita(no.direita)
            return self._rotacao_esquerda(no)

        return no

    def _inserir_recursivo(
        self, no: _NoAVL | None, data: date, ocorrencia_id: str
    ) -> tuple[_NoAVL, bool]:
        if no is None:
            return _NoAVL(data=data, ocorrencia_id=ocorrencia_id), True

        chave_nova = (data, ocorrencia_id)
        chave_atual = no.chave

        if chave_nova < chave_atual:
            no.esquerda, inserido = self._inserir_recursivo(
                no.esquerda, data, ocorrencia_id
            )
        elif chave_nova > chave_atual:
            no.direita, inserido = self._inserir_recursivo(
                no.direita, data, ocorrencia_id
            )
        else:
            # Par (data, ocorrencia_id) já existe: não duplica
            return no, False

        if not inserido:
            return no, False

        return self._rebalancear(no), True

    def _remover_recursivo(
        self, no: _NoAVL | None, chave: tuple[date, str]
    ) -> tuple[_NoAVL | None, bool]:
        if no is None:
            return None, False

        chave_atual = no.chave

        if chave < chave_atual:
            no.esquerda, removido = self._remover_recursivo(no.esquerda, chave)
            if not removido:
                return no, False
        elif chave > chave_atual:
            no.direita, removido = self._remover_recursivo(no.direita, chave)
            if not removido:
                return no, False
        else:
            # Nó encontrado
            if no.esquerda is None:
                return no.direita, True
            if no.direita is None:
                return no.esquerda, True

            # Nó com dois filhos: substitui pelo sucessor em-ordem (menor da subárvore direita)
            sucessor = self._menor_no(no.direita)
            no.data = sucessor.data
            no.ocorrencia_id = sucessor.ocorrencia_id
            no.direita, _ = self._remover_recursivo(no.direita, sucessor.chave)

        return self._rebalancear(no), True

    def _menor_no(self, no: _NoAVL) -> _NoAVL:
        atual = no
        while atual.esquerda is not None:
            atual = atual.esquerda
        return atual

    def _buscar_periodo_recursivo(
        self, no: _NoAVL | None, inicio: date, fim: date
    ) -> Iterator[str]:
        if no is None:
            return

        if no.data >= inicio:
            yield from self._buscar_periodo_recursivo(no.esquerda, inicio, fim)

        if inicio <= no.data <= fim:
            yield no.ocorrencia_id

        if no.data <= fim:
            yield from self._buscar_periodo_recursivo(no.direita, inicio, fim)

