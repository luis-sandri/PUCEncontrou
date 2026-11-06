"""Núcleo interno de operações; não é um serviço HTTP ou de autorização."""

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Protocol

from app.erros import ErroValidacao, OcorrenciaNaoEncontrada
from app.models.alteracao_ocorrencias import (
    AlteracaoOcorrencia,
    LoteOcorrencias,
    validar_estado_ocorrencias,
)
from app.models.ocorrencia import Ocorrencia, SituacaoGuarda, StatusOcorrencia, TipoOcorrencia


class ArmazenamentoOcorrenciasPorta(Protocol):
    """Fronteira SCRUM-13: uma aplicação de lote deve ser indivisível.

    aplicar deve verificar as precondições e integridade com preparar_estado
    dentro da mesma região crítica da publicação. Qualquer falha mantém o
    estado anterior. Lista/AVL/JSON pertencem à implementação desta porta.
    Leituras devem oferecer snapshots coerentes com essa publicação.
    """

    def obter(self, ocorrencia_id: str) -> Ocorrencia | None: ...

    def listar(self) -> Iterable[Ocorrencia]: ...

    def aplicar(self, lote: LoteOcorrencias) -> None: ...


class NucleoOcorrencias:
    """Prepara CRUD e transições; o serviço SCRUM-16 autoriza e valida uploads.

    Não conectar diretamente a rotas. Uma confirmação só pode ser solicitada
    pelo serviço após validar ator, ação e confirmação presencial aplicáveis.
    Preparar não escreve. Desistir significa não chamar confirmar.
    """

    def __init__(self, armazenamento: ArmazenamentoOcorrenciasPorta) -> None:
        self._armazenamento = armazenamento

    def obter(self, ocorrencia_id: str) -> Ocorrencia:
        item = self._armazenamento.obter(ocorrencia_id)
        if item is None:
            raise OcorrenciaNaoEncontrada("Ocorrência não encontrada.")
        return item

    def listar(self, filtros: Mapping[str, object] | None = None) -> tuple[Ocorrencia, ...]:
        """Filtros exatos combinados por E; local e guarda são independentes."""
        if filtros is None:
            filtros = {}
        enums = {"tipo": TipoOcorrencia, "status": StatusOcorrencia, "situacao_guarda": SituacaoGuarda}
        textuais = {"categoria", "local_ocorrencia", "setor_guarda"}
        if not isinstance(filtros, Mapping) or set(filtros) - (set(enums) | textuais):
            raise ErroValidacao("Filtro desconhecido; use os nomes explícitos de local e guarda.")
        criterios = {}
        for campo, valor in filtros.items():
            if campo in enums:
                try:
                    valor = enums[campo](valor)
                except (ValueError, TypeError) as erro:
                    raise ErroValidacao(f"{campo}: filtro inválido.") from erro
            elif not isinstance(valor, str) or not valor.strip():
                raise ErroValidacao(f"{campo}: informe texto não vazio no filtro.")
            else:
                valor = valor.strip()
            criterios[campo] = valor
        return tuple(item for item in self._armazenamento.listar()
                     if all(getattr(item, campo) == valor for campo, valor in criterios.items()))

    def preparar_cadastro(self, dados: Mapping[str, object]) -> LoteOcorrencias:
        item = Ocorrencia.criar(dados)
        return self._preparar(self._estado(), AlteracaoOcorrencia(None, item))

    def preparar_edicao(self, ocorrencia_id: str, dados: Mapping[str, object]) -> LoteOcorrencias:
        estado = self._estado()
        item = self._buscar(estado, ocorrencia_id)
        return self._preparar(estado, AlteracaoOcorrencia(item, item.corrigir(dados)))

    def preparar_exclusao(self, ocorrencia_id: str) -> LoteOcorrencias:
        estado = self._estado()
        grupo = self._grupo(estado, ocorrencia_id)
        alteracoes = [AlteracaoOcorrencia(grupo[0], None)]
        if len(grupo) == 2:
            parceiro = grupo[1]
            alteracoes.append(AlteracaoOcorrencia(parceiro, replace(parceiro, vinculo_id=None)))
        return self._preparar(estado, *alteracoes)

    def preparar_vinculo(self, perdido_id: str, encontrado_id: str) -> LoteOcorrencias:
        estado = self._estado()
        perdido, encontrado = self._buscar(estado, perdido_id), self._buscar(estado, encontrado_id)
        if perdido.tipo is not TipoOcorrencia.PERDIDO or encontrado.tipo is not TipoOcorrencia.ENCONTRADO:
            raise ErroValidacao("Vincule um PERDIDO a um ENCONTRADO, nessa ordem.")
        if any(item.status is not StatusOcorrencia.ABERTO or item.vinculo_id is not None
               for item in (perdido, encontrado)):
            raise ErroValidacao("Somente ocorrências abertas e sem parceiro podem ser vinculadas.")
        return self._preparar(
            estado,
            AlteracaoOcorrencia(perdido, replace(perdido, vinculo_id=encontrado.id)),
            AlteracaoOcorrencia(encontrado, replace(encontrado, vinculo_id=perdido.id)),
        )

    def preparar_resolucao(self, ocorrencia_id: str) -> LoteOcorrencias:
        return self._preparar_status(ocorrencia_id, StatusOcorrencia.RESOLVIDO)

    def preparar_reabertura(self, ocorrencia_id: str) -> LoteOcorrencias:
        return self._preparar_status(ocorrencia_id, StatusOcorrencia.ABERTO)

    def preparar_cancelamento(self, ocorrencia_id: str) -> LoteOcorrencias:
        return self._preparar_status(ocorrencia_id, StatusOcorrencia.CANCELADO)

    def confirmar(self, lote: LoteOcorrencias) -> None:
        """Delega a aplicação indivisível; não faz checagem fora do lock da porta."""
        if not isinstance(lote, LoteOcorrencias):
            raise ErroValidacao("Informe um lote de alterações válido.")
        self._armazenamento.aplicar(lote)

    def _preparar_status(self, ocorrencia_id: str, destino: StatusOcorrencia) -> LoteOcorrencias:
        estado = self._estado()
        grupo = self._grupo(estado, ocorrencia_id)
        origem = grupo[0].status
        if (destino is origem
                or (destino is not StatusOcorrencia.ABERTO and origem is not StatusOcorrencia.ABERTO)):
            raise ErroValidacao("Transição inválida; reabra a ocorrência antes de outro encerramento.")
        if destino is StatusOcorrencia.CANCELADO and len(grupo) == 2:
            raise ErroValidacao("Cancelamento de ocorrência vinculada aguarda política de propagação.")
        return self._preparar(estado, *(AlteracaoOcorrencia(item, replace(item, status=destino))
                                       for item in grupo))

    def _estado(self) -> tuple[Ocorrencia, ...]:
        estado = tuple(self._armazenamento.listar())
        validar_estado_ocorrencias(estado)
        return estado

    @staticmethod
    def _buscar(estado: tuple[Ocorrencia, ...], ocorrencia_id: str) -> Ocorrencia:
        for item in estado:
            if item.id == ocorrencia_id:
                return item
        raise OcorrenciaNaoEncontrada("Ocorrência não encontrada.")

    def _grupo(self, estado: tuple[Ocorrencia, ...], ocorrencia_id: str) -> tuple[Ocorrencia, ...]:
        item = self._buscar(estado, ocorrencia_id)
        if item.vinculo_id is None:
            return (item,)
        return item, self._buscar(estado, item.vinculo_id)

    @staticmethod
    def _preparar(estado: tuple[Ocorrencia, ...], *alteracoes: AlteracaoOcorrencia) -> LoteOcorrencias:
        lote = LoteOcorrencias(alteracoes)
        lote.preparar_estado(estado)
        return lote
