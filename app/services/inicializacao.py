"""Integração da persistência JSON com Lista Dinâmica e Árvore AVL.

Responsabilidade de Matheus (SCRUM-13). Reconstrução das estruturas manuais
ao iniciar e armazenamento integrado com garantia de atomicidade.
"""

from collections.abc import Callable, Iterable, Mapping
from datetime import date
from threading import RLock

from app.composicao import DependenciasOcorrencias
from app.erros import ErroValidacao
from app.models.alteracao_ocorrencias import LoteOcorrencias, validar_estado_ocorrencias
from app.models.ocorrencia import Ocorrencia, OcorrenciaPorta
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON, RepositorioOcorrenciasPorta
from app.services.consultas import ServicoConsultaPeriodo
from app.services.nucleo_ocorrencias import ArmazenamentoOcorrenciasPorta, NucleoOcorrencias
from app.structures.avl import ArvoreAVL, IndiceDatasPorta
from app.structures.lista_dinamica import ListaDinamica, ListaDinamicaPorta


def inicializar_ocorrencias(
    repositorio: RepositorioOcorrenciasPorta,
    lista: ListaDinamicaPorta[OcorrenciaPorta],
    indice: IndiceDatasPorta,
    extrair_data: Callable[[OcorrenciaPorta], date] = lambda o: o.data_ocorrencia,
) -> None:
    """Carrega o snapshot JSON, valida a integridade e povoa a Lista manual e a AVL.

    Exige destinos vazios para prevenir duplicações acidentais.
    Falhas de validação ou leitura abortam sem publicar estado inconsistente.
    """
    if len(lista) > 0:
        raise ErroValidacao("A Lista Dinâmica de destino deve estar vazia para a inicialização.")

    itens = tuple(repositorio.carregar())
    validar_estado_ocorrencias(itens)

    for item in itens:
        lista.inserir(item)
        data = extrair_data(item)
        indice.inserir(data, item.id)


class ArmazenamentoOcorrencias:
    """Armazenamento integrado compatível com ArmazenamentoOcorrenciasPorta.

    Coordena a Lista Dinâmica manual (armazenamento em memória), a Árvore AVL
    (índice temporal por chave composta) e o repositório JSON (persistência).
    Mutações seguem o princípio de falha segura: o novo estado é preparado e
    validado, persistido atomicamente no JSON e só então publicado nas estruturas
    em memória. Se houver falha de I/O, o estado anterior é preservado.
    """

    def __init__(
        self,
        repositorio: RepositorioOcorrenciasPorta,
        lista: ListaDinamicaPorta[OcorrenciaPorta],
        indice: IndiceDatasPorta,
        extrair_data: Callable[[OcorrenciaPorta], date] = lambda o: o.data_ocorrencia,
    ) -> None:
        self._repositorio = repositorio
        self._lista = lista
        self._indice = indice
        self._extrair_data = extrair_data
        self._lock = RLock()

    def obter(self, ocorrencia_id: str) -> Ocorrencia | None:
        with self._lock:
            for item in self._lista:
                if item.id == ocorrencia_id:
                    return item
            return None

    def listar(self) -> tuple[Ocorrencia, ...]:
        with self._lock:
            return tuple(self._lista)

    def _posicao_na_lista(self, ocorrencia_id: str) -> int | None:
        for idx, item in enumerate(self._lista):
            if item.id == ocorrencia_id:
                return idx
        return None

    def aplicar(self, lote: LoteOcorrencias) -> None:
        if not isinstance(lote, LoteOcorrencias):
            raise ErroValidacao("Informe um lote de alterações válido.")

        with self._lock:
            estado_atual = tuple(self._lista)
            # 1. Prepara e valida novo estado como snapshot transitório
            novo_estado = lote.preparar_estado(estado_atual)

            # 2. Persiste atomicamente no JSON ANTES de alterar a memória
            # Se salvar() lançar ErroPersistencia, a memória permanece inalterada
            self._repositorio.salvar(novo_estado)

            # 3. Publica as alterações nas estruturas manuais em memória
            for alteracao in lote.alteracoes:
                if alteracao.anterior is None and alteracao.posterior is not None:
                    # Cadastro de nova ocorrência
                    self._lista.inserir(alteracao.posterior)
                    data = self._extrair_data(alteracao.posterior)
                    self._indice.inserir(data, alteracao.posterior.id)

                elif alteracao.anterior is not None and alteracao.posterior is None:
                    # Exclusão física
                    pos = self._posicao_na_lista(alteracao.anterior.id)
                    if pos is not None:
                        self._lista.remover(pos)
                    data = self._extrair_data(alteracao.anterior)
                    self._indice.remover(data, alteracao.anterior.id)

                elif alteracao.anterior is not None and alteracao.posterior is not None:
                    # Atualização (edição, status, vínculo, data)
                    pos = self._posicao_na_lista(alteracao.anterior.id)
                    if pos is not None:
                        self._lista.atualizar(pos, alteracao.posterior)
                    data_antiga = self._extrair_data(alteracao.anterior)
                    data_nova = self._extrair_data(alteracao.posterior)
                    if data_antiga != data_nova:
                        self._indice.remover(data_antiga, alteracao.anterior.id)
                        self._indice.inserir(data_nova, alteracao.posterior.id)


def compor_producao(config: Mapping[str, object]) -> DependenciasOcorrencias:
    """Compositor concreto de ocorrências para a fábrica Flask."""
    caminho = config.get("OCORRENCIAS_JSON")
    repositorio = RepositorioOcorrenciasJSON(caminho)
    repositorio.inicializar()

    lista = ListaDinamica[OcorrenciaPorta]()
    indice = ArvoreAVL()

    inicializar_ocorrencias(repositorio, lista, indice)
    armazenamento = ArmazenamentoOcorrencias(repositorio, lista, indice)
    nucleo = NucleoOcorrencias(armazenamento)
    consulta = ServicoConsultaPeriodo(indice, armazenamento.obter)

    return DependenciasOcorrencias(nucleo=nucleo, consulta_periodo=consulta)
