"""Vocabulário aprovado e visão mínima proposta para Marcelo revisar.

OcorrenciaPorta é somente um contrato de leitura. Não é o modelo concreto.
Campos de formulário, data, locais, categoria e vínculo aguardam definição.
"""

from enum import Enum
from typing import Protocol


class TipoOcorrencia(str, Enum):
    PERDIDO = "PERDIDO"
    ENCONTRADO = "ENCONTRADO"


class StatusOcorrencia(str, Enum):
    ABERTO = "ABERTO"
    RESOLVIDO = "RESOLVIDO"
    CANCELADO = "CANCELADO"


class OcorrenciaPorta(Protocol):
    """Identidade opaca e estado; sem acesso ao armazenamento interno."""

    @property
    def id(self) -> str: ...

    @property
    def tipo(self) -> TipoOcorrencia: ...

    @property
    def status(self) -> StatusOcorrencia: ...
