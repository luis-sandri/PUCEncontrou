"""Modelo imutável e codec de ocorrências, sem Flask ou acesso a arquivos."""

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import date
from enum import Enum
from typing import Protocol
from uuid import uuid4

from app.erros import ErroValidacao


class TipoOcorrencia(str, Enum):
    PERDIDO = "PERDIDO"
    ENCONTRADO = "ENCONTRADO"


class StatusOcorrencia(str, Enum):
    ABERTO = "ABERTO"
    RESOLVIDO = "RESOLVIDO"
    CANCELADO = "CANCELADO"


class SituacaoGuarda(str, Enum):
    AINDA_NAO_ENTREGUE = "AINDA_NAO_ENTREGUE"
    EM_SETOR = "EM_SETOR"


class OcorrenciaPorta(Protocol):
    """Identidade opaca e estado; sem acesso ao armazenamento interno."""

    @property
    def id(self) -> str: ...

    @property
    def tipo(self) -> TipoOcorrencia: ...

    @property
    def status(self) -> StatusOcorrencia: ...


def _texto(valor: object, campo: str, *, obrigatorio: bool = True) -> str | None:
    if valor is None and not obrigatorio:
        return None
    if not isinstance(valor, str):
        raise ErroValidacao(f"{campo}: informe texto válido.")
    controles_permitidos = "\n\r\t" if campo == "descricao" else ""
    if any(ord(c) < 32 and c not in controles_permitidos for c in valor):
        raise ErroValidacao(f"{campo}: informe texto válido.")
    texto = valor.strip()
    if not texto:
        if not obrigatorio:
            return None
        raise ErroValidacao(f"{campo}: preenchimento obrigatório.")
    return texto


def _enum(valor: object, classe: type[Enum], campo: str) -> Enum:
    try:
        return classe(valor)
    except (TypeError, ValueError) as erro:
        raise ErroValidacao(f"{campo}: valor inválido.") from erro


def _validar_campos(dados: Mapping[str, object], permitidos: set[str]) -> None:
    if not isinstance(dados, Mapping):
        raise ErroValidacao("Informe um mapeamento de campos.")
    if set(dados) - permitidos:
        raise ErroValidacao("Campos desconhecidos ou controlados pela operação.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Ocorrencia:
    """Estado validado. Alterações de status/vínculo são coordenadas pelo núcleo.

    A referência da foto é relativa à raiz de imagens da aplicação. Validar
    seus bytes, existência e associação ao upload cabe ao serviço SCRUM-16.
    """

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
    situacao_guarda: SituacaoGuarda | None = None
    setor_guarda: str | None = None
    data_recebimento: date | None = None
    destinacao_a_verificar: bool = False
    vinculo_id: str | None = None

    def __post_init__(self) -> None:
        for campo in ("id", "nome", "categoria", "local_ocorrencia", "foto_referencia"):
            object.__setattr__(self, campo, _texto(getattr(self, campo), campo))
        for campo in ("descricao", "cor", "setor_guarda"):
            object.__setattr__(self, campo, _texto(getattr(self, campo), campo, obrigatorio=False))
        if self.vinculo_id is not None:
            object.__setattr__(self, "vinculo_id", _texto(self.vinculo_id, "vinculo_id"))
        object.__setattr__(self, "tipo", _enum(self.tipo, TipoOcorrencia, "tipo"))
        object.__setattr__(self, "status", _enum(self.status, StatusOcorrencia, "status"))
        if type(self.data_ocorrencia) is not date:
            raise ErroValidacao("data_ocorrencia: informe uma data de calendário.")
        if self.data_recebimento is not None and type(self.data_recebimento) is not date:
            raise ErroValidacao("data_recebimento: informe uma data de calendário.")
        if type(self.destinacao_a_verificar) is not bool:
            raise ErroValidacao("destinacao_a_verificar: informe verdadeiro ou falso.")
        referencia = self.foto_referencia
        if (any(c in referencia for c in "\\:?#")
                or any(parte in ("", ".", "..") for parte in referencia.split("/"))):
            raise ErroValidacao("foto_referencia: use caminho local relativo, sem navegação de diretórios.")
        if self.vinculo_id == self.id:
            raise ErroValidacao("vinculo_id: uma ocorrência não pode vincular a si mesma.")
        self._validar_guarda()

    def _validar_guarda(self) -> None:
        if self.tipo is TipoOcorrencia.PERDIDO:
            if (self.situacao_guarda is not None or self.setor_guarda is not None
                    or self.data_recebimento is not None or self.destinacao_a_verificar):
                raise ErroValidacao("Guarda, recebimento e destinação pertencem somente a ENCONTRADO.")
            return
        situacao = (SituacaoGuarda.AINDA_NAO_ENTREGUE if self.situacao_guarda is None
                    else _enum(self.situacao_guarda, SituacaoGuarda, "situacao_guarda"))
        object.__setattr__(self, "situacao_guarda", situacao)
        if situacao is SituacaoGuarda.EM_SETOR:
            if self.setor_guarda is None:
                raise ErroValidacao("setor_guarda: informe o setor que guarda o objeto.")
        elif self.setor_guarda is not None or self.data_recebimento is not None:
            raise ErroValidacao("Objeto ainda não entregue não possui setor ou recebimento pelo setor.")

    @classmethod
    def criar(cls, dados: Mapping[str, object]) -> "Ocorrencia":
        """Gera identidade no backend e sempre começa ABERTO."""
        permitidos = {campo.name for campo in fields(cls)} - {"id", "status", "vinculo_id"}
        _validar_campos(dados, permitidos)
        cls._validar_obrigatorios(dados, {"tipo", "nome", "categoria", "data_ocorrencia",
                                         "local_ocorrencia", "foto_referencia"})
        return cls(id=str(uuid4()), **dados)

    def corrigir(self, dados: Mapping[str, object]) -> "Ocorrencia":
        """Não permite alterar identidade, tipo, status ou vínculo por edição."""
        permitidos = {campo.name for campo in fields(self)} - {"id", "tipo", "status", "vinculo_id"}
        _validar_campos(dados, permitidos)
        return replace(self, **dados)

    def para_registro(self) -> dict[str, object]:
        """Produz valores JSON; não grava arquivo ou envelope de repositório."""
        registro = {}
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if isinstance(valor, Enum):
                valor = valor.value
            elif type(valor) is date:
                valor = valor.isoformat()
            registro[campo.name] = valor
        return registro

    @classmethod
    def de_registro(cls, registro: Mapping[str, object]) -> "Ocorrencia":
        """Reidrata sem gerar ID ou substituir status, datas e vínculos."""
        _validar_campos(registro, {campo.name for campo in fields(cls)})
        cls._validar_obrigatorios(registro, {"id", "tipo", "status", "nome", "categoria",
                                            "data_ocorrencia", "local_ocorrencia", "foto_referencia"})
        dados = dict(registro)
        for campo in ("data_ocorrencia", "data_recebimento"):
            valor = dados.get(campo)
            if valor is None and campo == "data_recebimento":
                continue
            try:
                if not isinstance(valor, str) or len(valor) != 10:
                    raise ValueError
                convertido = date.fromisoformat(valor)
                if convertido.isoformat() != valor:
                    raise ValueError
            except (ValueError, TypeError) as erro:
                raise ErroValidacao(f"{campo}: use uma data válida em AAAA-MM-DD.") from erro
            dados[campo] = convertido
        return cls(**dados)

    @staticmethod
    def _validar_obrigatorios(dados: Mapping[str, object], campos: set[str]) -> None:
        ausentes = campos - set(dados)
        if ausentes:
            raise ErroValidacao(f"Campos obrigatórios ausentes: {', '.join(sorted(ausentes))}.")
