"""Fronteira de Luís: entrada, autorização e uploads; domínio delegado ao núcleo."""

from collections.abc import Iterable, Mapping
from datetime import date
from enum import Enum
from typing import BinaryIO, Protocol

from app.erros import ErroValidacao, PermissaoNegada
from app.models.conta import ContaAdministrativaPorta, Perfil
from app.models.ocorrencia import OcorrenciaPorta, StatusOcorrencia, TipoOcorrencia
from app.repositories.contas import RepositorioContasPorta
from app.services.consultas import ConsultaPeriodoPorta
from app.repositories.fotos import RepositorioFotosPorta


class AlteracaoPreparadaPorta(Protocol):
    @property
    def posterior(self) -> OcorrenciaPorta | None: ...


class LotePreparadoPorta(Protocol):
    @property
    def alteracoes(self) -> tuple[AlteracaoPreparadaPorta, ...]: ...


class NucleoOcorrenciasPorta(Protocol):
    """Consumidor do contrato publicado de Marcelo; não implementa CRUD."""

    def obter(self, ocorrencia_id: str) -> OcorrenciaPorta: ...
    def listar(self, filtros: Mapping[str, object] | None = None) -> Iterable[OcorrenciaPorta]: ...
    def preparar_cadastro(self, dados: Mapping[str, object]) -> LotePreparadoPorta: ...
    def preparar_edicao(self, ocorrencia_id: str, dados: Mapping[str, object]) -> LotePreparadoPorta: ...
    def preparar_exclusao(self, ocorrencia_id: str) -> LotePreparadoPorta: ...
    def preparar_vinculo(self, perdido_id: str, encontrado_id: str) -> LotePreparadoPorta: ...
    def preparar_resolucao(self, ocorrencia_id: str) -> LotePreparadoPorta: ...
    def preparar_reabertura(self, ocorrencia_id: str) -> LotePreparadoPorta: ...
    def preparar_cancelamento(self, ocorrencia_id: str) -> LotePreparadoPorta: ...
    def confirmar(self, lote: LotePreparadoPorta) -> None: ...


CAMPOS_OBJETO = {"nome", "categoria", "data_ocorrencia", "local_ocorrencia", "descricao", "cor"}
CAMPOS_GUARDA = {"situacao_guarda", "setor_guarda"}
CAMPOS_INTERNOS = {"data_recebimento", "destinacao_a_verificar"}
FILTROS = {"tipo", "status", "categoria", "local_ocorrencia", "situacao_guarda", "setor_guarda"}


def _data(valor: object, campo: str, *, opcional=False) -> date | None:
    if opcional and valor in (None, ""):
        return None
    if type(valor) is date:
        return valor
    try:
        if not isinstance(valor, str) or len(valor) != 10:
            raise ValueError
        resultado = date.fromisoformat(valor)
        if resultado.isoformat() != valor:
            raise ValueError
        return resultado
    except ValueError:
        raise ErroValidacao(f"{campo}: informe uma data válida.") from None


def _texto(valor: object, campo: str, *, obrigatorio=False) -> str:
    if valor is None and not obrigatorio:
        return ""
    if not isinstance(valor, str) or (obrigatorio and not valor.strip()):
        raise ErroValidacao(f"{campo}: preenchimento obrigatório.")
    return valor.strip()


def _valor(valor):
    return valor.value if isinstance(valor, Enum) else valor


class AtendimentoOcorrencias:
    def __init__(self, nucleo: NucleoOcorrenciasPorta, consulta_periodo: ConsultaPeriodoPorta,
                 contas: RepositorioContasPorta, fotos: RepositorioFotosPorta, *,
                 setor_publico: bool = True, cancelamento_habilitado: bool = True) -> None:
        self._nucleo = nucleo
        self._consulta_periodo = consulta_periodo
        self._contas = contas
        self._fotos = fotos
        self.setor_publico = setor_publico
        self.cancelamento_habilitado = cancelamento_habilitado

    def exigir_secretario(self, ator: ContaAdministrativaPorta) -> None:
        conta_id = getattr(ator, "id", None)
        conta = self._contas.buscar_por_id(conta_id) if isinstance(conta_id, str) else None
        if (conta is None or not conta.ativa or conta.perfil is not Perfil.SECRETARIO
                or conta.versao_sessao != getattr(ator, "versao_sessao", None)):
            raise PermissaoNegada("Esta operação exige secretário autenticado e ativo.")

    def obter(self, ocorrencia_id: str) -> OcorrenciaPorta:
        return self._nucleo.obter(ocorrencia_id)

    def listar(self, filtros: Mapping[str, object] | None = None) -> tuple[OcorrenciaPorta, ...]:
        filtros = {} if filtros is None else filtros
        if not isinstance(filtros, Mapping) or set(filtros) - (FILTROS | {"inicio", "fim", "q"}):
            raise ErroValidacao("Filtro desconhecido.")
        criterios = {chave: _texto(valor, chave) for chave, valor in filtros.items() if chave in FILTROS and valor not in (None, "")}
        for campo, classe in (("tipo", TipoOcorrencia), ("status", StatusOcorrencia)):
            if campo in criterios:
                try:
                    classe(criterios[campo])
                except ValueError:
                    raise ErroValidacao(f"{campo}: filtro inválido.") from None
        if "situacao_guarda" in criterios and criterios["situacao_guarda"] not in {"EM_SETOR", "AINDA_NAO_ENTREGUE"}:
            raise ErroValidacao("Situação de guarda inválida.")
        if not self.setor_publico and set(criterios) & CAMPOS_GUARDA:
            raise ErroValidacao("Filtro de guarda não está disponível na consulta pública.")
        inicio, fim = filtros.get("inicio"), filtros.get("fim")
        if inicio or fim:
            a, b = _data(inicio, "inicio"), _data(fim, "fim")
            if a > b:
                raise ErroValidacao("O início do período deve ser anterior ou igual ao fim.")
            candidatos = self._consulta_periodo.buscar_periodo(a, b)
        else:
            candidatos = self._nucleo.listar(criterios)
        busca = _texto(filtros.get("q"), "q").casefold()
        resultado = []
        for item in candidatos:
            if not all(_valor(getattr(item, campo)) == valor for campo, valor in criterios.items()):
                continue
            texto = " ".join(str(getattr(item, campo, "") or "") for campo in ("id", "nome", "descricao"))
            if not busca or busca in texto.casefold():
                resultado.append(item)
        return tuple(resultado)

    def visao(self, item: OcorrenciaPorta, *, ator=None, interna=False) -> dict[str, object]:
        if interna:
            self.exigir_secretario(ator)
        campos = {"id", "tipo", "status", "nome", "categoria", "data_ocorrencia", "local_ocorrencia", "descricao", "cor"}
        if self.setor_publico or interna:
            campos |= CAMPOS_GUARDA
        if interna:
            campos |= CAMPOS_INTERNOS | {"vinculo_id"}
        resultado = {}
        for campo in campos:
            valor = _valor(getattr(item, campo, None))
            resultado[campo] = valor.isoformat() if type(valor) is date else valor
        return resultado

    def _dados(self, dados: Mapping[str, object], *, cadastro=False) -> dict[str, object]:
        permitidos = CAMPOS_OBJETO | CAMPOS_GUARDA | ({"tipo"} if cadastro else CAMPOS_INTERNOS)
        if not isinstance(dados, Mapping) or set(dados) - permitidos:
            raise ErroValidacao("Campo desconhecido ou controlado pelo sistema.")
        resultado = {}
        for campo in dados:
            valor = dados[campo]
            if campo == "data_ocorrencia":
                valor = _data(valor, campo)
            elif campo == "data_recebimento":
                valor = _data(valor, campo, opcional=True)
            elif campo == "destinacao_a_verificar":
                if type(valor) is not bool:
                    raise ErroValidacao("Destinação: informe verdadeiro ou falso.")
            else:
                valor = _texto(valor, campo, obrigatorio=campo in {"nome", "categoria", "local_ocorrencia", "tipo"})
            resultado[campo] = valor
        if cadastro:
            for campo in ("nome", "categoria", "data_ocorrencia", "local_ocorrencia", "tipo"):
                if campo not in resultado:
                    raise ErroValidacao(f"{campo}: preenchimento obrigatório.")
            try:
                TipoOcorrencia(resultado["tipo"])
            except ValueError:
                raise ErroValidacao("Tipo de ocorrência inválido.") from None
        if "situacao_guarda" in resultado:
            if resultado["situacao_guarda"] == "":
                resultado["situacao_guarda"] = None
            elif resultado["situacao_guarda"] not in {"EM_SETOR", "AINDA_NAO_ENTREGUE"}:
                raise ErroValidacao("Situação de guarda inválida.")
        return resultado

    def _confirmar(self, lote):
        self._nucleo.confirmar(lote)
        return tuple(a.posterior for a in lote.alteracoes if a.posterior is not None)

    def _com_foto(self, dados, arquivo, preparar, *, obrigatoria):
        if arquivo is None and obrigatoria:
            raise ErroValidacao("Envie a foto obrigatória do objeto.")
        referencia = None
        try:
            if arquivo is not None:
                referencia = self._fotos.salvar(arquivo)
                dados["foto_referencia"] = referencia
            return self._confirmar(preparar(dados))
        except Exception:
            if referencia is not None:
                self._fotos.remover(referencia)
            raise

    def cadastrar(self, dados: Mapping[str, object], *, foto: BinaryIO | None) -> OcorrenciaPorta:
        valores = self._dados(dados, cadastro=True)
        return self._com_foto(valores, foto, self._nucleo.preparar_cadastro, obrigatoria=True)[0]

    def editar(self, ocorrencia_id: str, dados: Mapping[str, object], *, ator, foto: BinaryIO | None = None) -> OcorrenciaPorta:
        self.exigir_secretario(ator)
        valores = self._dados(dados)
        preparar = lambda entrada: self._nucleo.preparar_edicao(ocorrencia_id, entrada)
        return self._com_foto(valores, foto, preparar, obrigatoria=False)[0]

    def excluir(self, ocorrencia_id: str, *, ator, confirmacao=False) -> None:
        self.exigir_secretario(ator)
        if confirmacao is not True:
            raise ErroValidacao("Confirme a exclusão da ocorrência.")
        self._confirmar(self._nucleo.preparar_exclusao(ocorrencia_id))
        # Descarte de fotos antigas continua pendente em P04; não remover arquivos aqui.

    def vincular(self, perdido_id: str, encontrado_id: str, *, ator):
        self.exigir_secretario(ator)
        return self._confirmar(self._nucleo.preparar_vinculo(perdido_id, encontrado_id))

    def alterar_status(self, ocorrencia_id: str, novo_status: StatusOcorrencia, *, ator, contexto: Mapping[str, object]):
        self.exigir_secretario(ator)
        if not isinstance(contexto, Mapping) or set(contexto) - {"confirmacao_presencial"}:
            raise ErroValidacao("Contexto de alteração inválido.")
        if novo_status is StatusOcorrencia.RESOLVIDO:
            if contexto.get("confirmacao_presencial") is not True:
                raise ErroValidacao("Confirme a devolução presencial antes de resolver.")
            lote = self._nucleo.preparar_resolucao(ocorrencia_id)
        elif novo_status is StatusOcorrencia.ABERTO:
            lote = self._nucleo.preparar_reabertura(ocorrencia_id)
        elif novo_status is StatusOcorrencia.CANCELADO and self.cancelamento_habilitado:
            lote = self._nucleo.preparar_cancelamento(ocorrencia_id)
        else:
            raise ErroValidacao("Cancelamento indisponível ou status inválido.")
        return self._confirmar(lote)

    def foto_publica(self, ocorrencia_id: str):
        item = self._nucleo.obter(ocorrencia_id)
        return self._fotos.ler(item.foto_referencia)
