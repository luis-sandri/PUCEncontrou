"""Ponto de integração de Luís com o núcleo e a carga real dos colegas."""

from dataclasses import dataclass
from importlib import import_module

from app.services.atendimento_ocorrencias import NucleoOcorrenciasPorta
from app.services.consultas import ConsultaPeriodoPorta


@dataclass(frozen=True)
class DependenciasOcorrencias:
    nucleo: NucleoOcorrenciasPorta
    consulta_periodo: ConsultaPeriodoPorta


def compor_ocorrencias(config) -> DependenciasOcorrencias:
    """O compositor externo carrega JSON, Lista e AVL antes de devolver dependências."""
    compositor = config.get("OCORRENCIAS_COMPOSITOR")
    if isinstance(compositor, str):
        modulo, separador, nome = compositor.partition(":")
        if not separador or not modulo or not nome:
            raise RuntimeError("Use OCORRENCIAS_COMPOSITOR no formato modulo:funcao.")
        try:
            compositor = getattr(import_module(modulo), nome)
        except (ImportError, AttributeError):
            raise RuntimeError("Compositor de ocorrências não está disponível.") from None
    if not callable(compositor):
        raise RuntimeError("Forneça o compositor concreto de ocorrências antes de habilitar suas rotas.")
    dependencias = compositor(config)
    if not isinstance(dependencias, DependenciasOcorrencias):
        raise RuntimeError("O compositor deve devolver DependenciasOcorrencias.")
    exigidos = {
        "nucleo": ("obter", "listar", "preparar_cadastro", "preparar_edicao", "preparar_exclusao",
                   "preparar_vinculo", "preparar_resolucao", "preparar_reabertura", "preparar_cancelamento", "confirmar"),
        "consulta_periodo": ("buscar_periodo",),
    }
    for atributo, metodos in exigidos.items():
        objeto = getattr(dependencias, atributo)
        if (isinstance(objeto, type) or getattr(objeto, "_is_protocol", False)
                or any(not callable(getattr(objeto, metodo, None)) for metodo in metodos)):
            raise RuntimeError(f"Dependência concreta inválida: {atributo}.")
    return dependencias
