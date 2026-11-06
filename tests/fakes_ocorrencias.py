"""Fakes de contrato, exclusivos de testes; não substituem Lista/AVL/JSON reais."""

from dataclasses import dataclass, replace
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.erros import ErroPersistencia, ErroValidacao, OcorrenciaNaoEncontrada
from app.models.ocorrencia import StatusOcorrencia, TipoOcorrencia


@dataclass(frozen=True, kw_only=True)
class RegistroFake:
    id: str
    tipo: TipoOcorrencia
    nome: str
    categoria: str
    data_ocorrencia: date
    local_ocorrencia: str
    foto_referencia: str
    descricao: str | None = None
    cor: str | None = None
    status: StatusOcorrencia = StatusOcorrencia.ABERTO
    situacao_guarda: str | None = None
    setor_guarda: str | None = None
    data_recebimento: date | None = None
    destinacao_a_verificar: bool = False
    vinculo_id: str | None = None


class NucleoFake:
    def __init__(self):
        self.itens = {}
        self.falhar = False

    def obter(self, identificador):
        if identificador not in self.itens:
            raise OcorrenciaNaoEncontrada("Ocorrência não encontrada.")
        return self.itens[identificador]

    def listar(self, filtros=None):
        return tuple(item for item in self.itens.values()
                     if all(getattr(item, chave) == valor for chave, valor in (filtros or {}).items()))

    def _lote(self, *pares):
        return SimpleNamespace(alteracoes=tuple(SimpleNamespace(anterior=a, posterior=b) for a, b in pares))

    def preparar_cadastro(self, dados):
        item = RegistroFake(id=str(uuid4()), **{**dados, "tipo": TipoOcorrencia(dados["tipo"])})
        return self._lote((None, item))

    def preparar_edicao(self, identificador, dados):
        anterior = self.obter(identificador)
        return self._lote((anterior, replace(anterior, **dados)))

    def preparar_exclusao(self, identificador):
        item = self.obter(identificador)
        pares = [(item, None)]
        if item.vinculo_id:
            outro = self.obter(item.vinculo_id)
            pares.append((outro, replace(outro, vinculo_id=None)))
        return self._lote(*pares)

    def preparar_vinculo(self, perdido_id, encontrado_id):
        a, b = self.obter(perdido_id), self.obter(encontrado_id)
        if (a.tipo is not TipoOcorrencia.PERDIDO or b.tipo is not TipoOcorrencia.ENCONTRADO
                or any(i.status is not StatusOcorrencia.ABERTO or i.vinculo_id for i in (a, b))):
            raise ErroValidacao("Par inválido.")
        return self._lote((a, replace(a, vinculo_id=b.id)), (b, replace(b, vinculo_id=a.id)))

    def _status(self, identificador, destino):
        item = self.obter(identificador)
        if item.status is destino or (destino is not StatusOcorrencia.ABERTO and item.status is not StatusOcorrencia.ABERTO):
            raise ErroValidacao("Transição inválida.")
        if destino is StatusOcorrencia.CANCELADO and item.vinculo_id:
            raise ErroValidacao("Cancelamento de par indisponível.")
        grupo = (item, self.obter(item.vinculo_id)) if item.vinculo_id else (item,)
        return self._lote(*((i, replace(i, status=destino)) for i in grupo))

    def preparar_resolucao(self, identificador):
        return self._status(identificador, StatusOcorrencia.RESOLVIDO)

    def preparar_reabertura(self, identificador):
        return self._status(identificador, StatusOcorrencia.ABERTO)

    def preparar_cancelamento(self, identificador):
        return self._status(identificador, StatusOcorrencia.CANCELADO)

    def confirmar(self, lote):
        if self.falhar:
            raise ErroPersistencia("Falha fictícia na confirmação.")
        for alteracao in lote.alteracoes:
            if alteracao.posterior is None:
                self.itens.pop(alteracao.anterior.id)
            else:
                self.itens[alteracao.posterior.id] = alteracao.posterior


class ConsultaFake:
    def __init__(self, nucleo):
        self.nucleo = nucleo
        self.chamadas = []

    def buscar_periodo(self, inicio, fim):
        self.chamadas.append((inicio, fim))
        return tuple(sorted((i for i in self.nucleo.listar() if inicio <= i.data_ocorrencia <= fim),
                            key=lambda i: (i.data_ocorrencia, i.id)))


def criar_nucleo():
    return NucleoFake()
