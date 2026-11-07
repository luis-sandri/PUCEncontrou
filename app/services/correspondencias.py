"""Sugestões determinísticas, sem mutação; política experimental explícita (P03)."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol
from unicodedata import combining, normalize

from app.erros import ErroValidacao
from app.models.ocorrencia import Ocorrencia, StatusOcorrencia
from app.services.ocorrencias import LeituraOcorrenciasPorta


class CandidatoCorrespondenciaPorta(Protocol):
    @property
    def ocorrencia_id(self) -> str: ...


class CorrespondenciasPorta(Protocol):
    def sugerir(self, ocorrencia_id: str) -> Sequence[CandidatoCorrespondenciaPorta]: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfiguracaoCorrespondencias:
    """Pesos relativos, limiar em 0–100 e limites escolhidos pelo integrador.

    Não há configuração de produção aprovada. A janela controla somente a
    contribuição da data: não exclui um par com outras evidências suficientes.
    """

    peso_categoria: float
    peso_cor: float
    peso_local: float
    peso_data: float
    peso_descricao: float
    limiar: float
    limite: int
    janela_dias: int

    def __post_init__(self) -> None:
        pesos = self.pesos
        for valor in (*pesos, self.limiar):
            if (type(valor) not in (int, float) or not isfinite(valor)
                    or valor < 0):
                raise ErroValidacao("Pesos e limiar devem ser números finitos não negativos.")
        if not isfinite(sum(pesos)) or sum(pesos) <= 0:
            raise ErroValidacao("A soma dos pesos deve ser finita e positiva.")
        if self.limiar > 100:
            raise ErroValidacao("O limiar deve estar entre 0 e 100.")
        if type(self.limite) is not int or self.limite <= 0:
            raise ErroValidacao("O limite deve ser um inteiro positivo.")
        if type(self.janela_dias) is not int or self.janela_dias < 0:
            raise ErroValidacao("A janela de datas deve ser um inteiro não negativo.")

    @property
    def pesos(self) -> tuple[float, ...]:
        return (self.peso_categoria, self.peso_cor, self.peso_local,
                self.peso_data, self.peso_descricao)


@dataclass(frozen=True, slots=True)
class CandidatoCorrespondencia:
    """Referência e pontuação experimental; não afirma propriedade do objeto."""

    ocorrencia_id: str
    pontuacao: float


def _normalizar(texto: str | None) -> str:
    """Ignora caixa, acentos, pontuação e espaços repetidos, sem sinônimos."""
    sem_acentos = "".join(c for c in normalize("NFD", (texto or "").casefold())
                          if not combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in sem_acentos).split())


def _igualdade(a: str | None, b: str | None) -> float:
    primeiro, segundo = _normalizar(a), _normalizar(b)
    return float(bool(primeiro) and primeiro == segundo)


def _descricao(a: str | None, b: str | None) -> float:
    primeiro, segundo = set(_normalizar(a).split()), set(_normalizar(b).split())
    if not primeiro or not segundo:
        return 0.0
    return len(primeiro & segundo) / len(primeiro | segundo)


class Correspondencias:
    """Implementa CorrespondenciasPorta sobre leitura do modelo completo.

    A dependência deve entregar Ocorrencia validada e leituras coerentes.
    Nenhum acesso a Lista, AVL, JSON, Flask ou operações de escrita é necessário.
    """

    def __init__(self, leitura: LeituraOcorrenciasPorta,
                 configuracao: ConfiguracaoCorrespondencias) -> None:
        self._leitura = leitura
        self._configuracao = configuracao

    def sugerir(self, ocorrencia_id: str) -> tuple[CandidatoCorrespondencia, ...]:
        # obter preserva OcorrenciaNaoEncontrada do serviço de leitura.
        origem = self._modelo(self._leitura.obter(ocorrencia_id))
        if not self._elegivel(origem):
            return ()

        # Índice temporário desta comparação, sem substituir o armazenamento
        # acadêmico. IDs repetidos iguais são colapsados; divergentes são erro.
        registros = {origem.id: origem}
        for valor in self._leitura.listar():
            item = self._modelo(valor)
            anterior = registros.get(item.id)
            if anterior is not None and anterior != item:
                raise ErroValidacao("Leitura inconsistente: estados diferentes para o mesmo ID.")
            registros[item.id] = item

        candidatos = []
        for item in registros.values():
            if (item.id == origem.id or item.tipo == origem.tipo
                    or not self._elegivel(item)):
                continue
            pontuacao = self._pontuar(origem, item)
            if pontuacao > 0 and pontuacao >= self._configuracao.limiar:
                candidatos.append(CandidatoCorrespondencia(item.id, pontuacao))

        candidatos.sort(key=lambda candidato: (-candidato.pontuacao, candidato.ocorrencia_id))
        return tuple(candidatos[:self._configuracao.limite])

    @staticmethod
    def _modelo(valor: object) -> Ocorrencia:
        if not isinstance(valor, Ocorrencia):
            raise ErroValidacao("A leitura de correspondências deve fornecer o modelo Ocorrencia completo.")
        return valor

    @staticmethod
    def _elegivel(item: Ocorrencia) -> bool:
        return item.status is StatusOcorrencia.ABERTO and item.vinculo_id is None

    def _pontuar(self, origem: Ocorrencia, item: Ocorrencia) -> float:
        config = self._configuracao
        distancia = abs((origem.data_ocorrencia - item.data_ocorrencia).days)
        if config.janela_dias == 0:
            proximidade = float(distancia == 0)
        else:
            proximidade = max(0.0, 1 - distancia / config.janela_dias)
        evidencias = (
            _igualdade(origem.categoria, item.categoria),
            _igualdade(origem.cor, item.cor),
            _igualdade(origem.local_ocorrencia, item.local_ocorrencia),
            proximidade,
            _descricao(origem.descricao, item.descricao),
        )
        # Denominador fixo: campos ausentes nunca aumentam os demais pesos.
        total = sum(peso * evidencia for peso, evidencia in zip(config.pesos, evidencias))
        return 100 * (total / sum(config.pesos))
