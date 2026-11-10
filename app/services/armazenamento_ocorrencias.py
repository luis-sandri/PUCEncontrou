"""Coordena Lista, AVL e snapshots JSON sob uma única publicação lógica."""

from collections.abc import Iterable
from datetime import date
from threading import RLock

from app.erros import ErroPersistencia, ErroValidacao
from app.models.alteracao_ocorrencias import LoteOcorrencias, validar_estado_ocorrencias
from app.models.ocorrencia import Ocorrencia
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON
from app.structures.avl import ArvoreAVL
from app.structures.lista_dinamica import ListaDinamica


class ArmazenamentoOcorrencias:
    """Publica estados completos só depois da validação e da gravação JSON."""

    def __init__(
        self,
        repositorio: RepositorioOcorrenciasJSON,
        ocorrencias: Iterable[Ocorrencia],
    ) -> None:
        self._repositorio = repositorio
        self._lock = RLock()
        estado = tuple(ocorrencias)
        validar_estado_ocorrencias(estado)
        self._lista, self._indice = self._construir_estruturas(estado)

    def obter(self, ocorrencia_id: str) -> Ocorrencia | None:
        with self._lock:
            indice = self._lista.buscar_indice(lambda item: item.id == ocorrencia_id)
            return None if indice is None else self._lista.obter(indice)

    def listar(self) -> tuple[Ocorrencia, ...]:
        with self._lock:
            return tuple(self._lista)

    def buscar_periodo(self, inicio: date, fim: date) -> tuple[Ocorrencia, ...]:
        with self._lock:
            ids = tuple(self._indice.buscar_periodo(inicio, fim))
            encontrados = []
            for ocorrencia_id in ids:
                indice = self._lista.buscar_indice(lambda item: item.id == ocorrencia_id)
                if indice is None:
                    raise ErroPersistencia("Índice temporal inconsistente com os registros.")
                encontrados.append(self._lista.obter(indice))
            return tuple(encontrados)

    def aplicar(self, lote: LoteOcorrencias) -> None:
        if not isinstance(lote, LoteOcorrencias):
            raise ErroValidacao("Informe um lote de alterações válido.")
        with self._lock:
            estado_anterior = tuple(self._lista)
            novo_estado = lote.preparar_estado(estado_anterior)
            nova_lista, novo_indice = self._construir_estruturas(novo_estado)
            self._repositorio.salvar(novo_estado)
            self._lista, self._indice = nova_lista, novo_indice

    @staticmethod
    def _construir_estruturas(
        estado: tuple[Ocorrencia, ...],
    ) -> tuple[ListaDinamica[Ocorrencia], ArvoreAVL]:
        validar_estado_ocorrencias(estado)
        lista = ListaDinamica[Ocorrencia]()
        indice = ArvoreAVL()
        for item in estado:
            if not isinstance(item, Ocorrencia):
                raise ErroValidacao("O armazenamento exige ocorrências validadas.")
            lista.inserir(item)
            indice.inserir(item.data_ocorrencia, item.id)
        return lista, indice


class ConsultaPeriodoAVL:
    """Resolve IDs da AVL para ocorrências sem expor nós às camadas externas."""

    def __init__(self, armazenamento: ArmazenamentoOcorrencias) -> None:
        self._armazenamento = armazenamento

    def buscar_periodo(self, inicio: date, fim: date) -> tuple[Ocorrencia, ...]:
        return self._armazenamento.buscar_periodo(inicio, fim)
