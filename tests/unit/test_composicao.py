"""A fábrica registra rotas somente com serviços concretos injetados."""

from types import SimpleNamespace

import pytest

from app import create_app
from app.composicao import DependenciasOcorrencias
from app.services.consultas import ConsultaPeriodoPorta
from tests.fakes_ocorrencias import ConsultaFake, criar_nucleo


def configuracao(tmp_path, **extra):
    return {"SECRET_KEY": "chave-isolada-de-teste", "CONTAS_HABILITADAS": True,
            "OCORRENCIAS_HABILITADAS": True, "CONTAS_JSON": tmp_path / "contas.json",
            "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json", "FOTOS_DIRETORIO": tmp_path / "fotos", **extra}


def test_sem_compositor_falha_sem_criar_arquivos(tmp_path):
    with pytest.raises(RuntimeError, match="compositor concreto"):
        create_app(configuracao(tmp_path, OCORRENCIAS_COMPOSITOR=None))
    assert list(tmp_path.iterdir()) == []


def test_ocorrencias_exigem_modulo_de_contas(tmp_path):
    with pytest.raises(RuntimeError, match="módulo de contas"):
        create_app(configuracao(tmp_path, CONTAS_HABILITADAS=False))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("dependencias", [None, SimpleNamespace(nucleo=None), DependenciasOcorrencias(None, None), DependenciasOcorrencias(None, ConsultaPeriodoPorta)])
def test_rejeita_composicao_invalida(tmp_path, dependencias):
    with pytest.raises(RuntimeError):
        create_app(configuracao(tmp_path, OCORRENCIAS_COMPOSITOR=lambda config: dependencias))
    assert list(tmp_path.iterdir()) == []


def test_compositor_chamado_uma_vez_e_instancias_isoladas(tmp_path):
    chamadas = []
    def compor(config):
        chamadas.append(config["OCORRENCIAS_JSON"])
        nucleo = criar_nucleo()
        return DependenciasOcorrencias(nucleo, ConsultaFake(nucleo))
    primeira = create_app(configuracao(tmp_path, OCORRENCIAS_COMPOSITOR=compor))
    segunda = create_app(configuracao(tmp_path, OCORRENCIAS_COMPOSITOR=compor))
    assert len(chamadas) == 2
    assert primeira.extensions["ocorrencias"] is not segunda.extensions["ocorrencias"]
    assert primeira.test_client().get("/ocorrencias").status_code == 200
    assert list(tmp_path.iterdir()) == []


def test_compositor_por_modulo_funcao(tmp_path, monkeypatch):
    import sys
    nucleo = criar_nucleo()
    monkeypatch.setitem(sys.modules, "compositor_ficticio", SimpleNamespace(
        compor=lambda config: DependenciasOcorrencias(nucleo, ConsultaFake(nucleo)),
    ))
    app = create_app(configuracao(tmp_path, OCORRENCIAS_COMPOSITOR="compositor_ficticio:compor"))
    assert app.test_client().get("/ocorrencias").status_code == 200
