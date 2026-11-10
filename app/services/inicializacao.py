"""Leitura validada do snapshot usado pela composição de produção."""

from collections.abc import Iterable

from app.models.alteracao_ocorrencias import validar_estado_ocorrencias
from app.models.ocorrencia import Ocorrencia


def carregar_snapshot_ocorrencias(
    ocorrencias: Iterable[Ocorrencia],
) -> tuple[Ocorrencia, ...]:
    """Valida o snapshot inteiro antes de construir Lista e índice temporal."""
    estado = tuple(ocorrencias)
    validar_estado_ocorrencias(estado)
    return estado
