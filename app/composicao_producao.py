"""Composição concreta de ocorrências com JSON, Lista manual e AVL manual."""

from app.composicao import DependenciasOcorrencias
from app.models.ocorrencia import Ocorrencia
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON
from app.services.armazenamento_ocorrencias import ArmazenamentoOcorrencias, ConsultaPeriodoAVL
from app.services.inicializacao import carregar_snapshot_ocorrencias
from app.services.nucleo_ocorrencias import NucleoOcorrencias


def compor_ocorrencias(config) -> DependenciasOcorrencias:
    repositorio = RepositorioOcorrenciasJSON(config["OCORRENCIAS_JSON"])
    estado = carregar_snapshot_ocorrencias(repositorio.carregar())
    if any(not isinstance(item, Ocorrencia) for item in estado):
        raise RuntimeError("O repositório devolveu ocorrências inválidas.")
    armazenamento = ArmazenamentoOcorrencias(repositorio, estado)
    return DependenciasOcorrencias(
        NucleoOcorrencias(armazenamento),
        ConsultaPeriodoAVL(armazenamento),
    )
