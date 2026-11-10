from datetime import date

import pytest

from app import create_app
from app.composicao import DependenciasOcorrencias
from app.erros import ErroPersistencia
from app.models.ocorrencia import Ocorrencia
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON
from app.services.armazenamento_ocorrencias import (
    ArmazenamentoOcorrencias,
    ConsultaPeriodoAVL,
)
from app.services.nucleo_ocorrencias import NucleoOcorrencias


def dados(**alteracoes):
    resultado = {
        "tipo": "PERDIDO",
        "nome": "Garrafa",
        "categoria": "Recipientes",
        "data_ocorrencia": date(2026, 11, 10),
        "local_ocorrencia": "Biblioteca",
        "foto_referencia": "ocorrencias/garrafa.jpg",
    }
    resultado.update(alteracoes)
    return resultado


def test_nucleo_persiste_e_reconstroi_lista_e_avl(tmp_path):
    repositorio = RepositorioOcorrenciasJSON(tmp_path / "ocorrencias.json")
    repositorio.inicializar()
    armazenamento = ArmazenamentoOcorrencias(repositorio, repositorio.carregar())
    nucleo = NucleoOcorrencias(armazenamento)

    lote = nucleo.preparar_cadastro(dados())
    ocorrencia_id = lote.alteracoes[0].id
    nucleo.confirmar(lote)

    recarregado = RepositorioOcorrenciasJSON(repositorio.caminho)
    nova_instancia = ArmazenamentoOcorrencias(recarregado, recarregado.carregar())
    consulta = ConsultaPeriodoAVL(nova_instancia)
    resultados = consulta.buscar_periodo(date(2026, 11, 10), date(2026, 11, 10))
    assert tuple(item.id for item in resultados) == (ocorrencia_id,)
    assert nova_instancia.obter(ocorrencia_id).nome == "Garrafa"


def test_falha_de_persistencia_nao_publica_lista_ou_indice(tmp_path, monkeypatch):
    repositorio = RepositorioOcorrenciasJSON(tmp_path / "ocorrencias.json")
    repositorio.inicializar()
    armazenamento = ArmazenamentoOcorrencias(repositorio, ())
    nucleo = NucleoOcorrencias(armazenamento)
    antes = repositorio.caminho.read_bytes()

    def falhar(_snapshot):
        raise ErroPersistencia("Falha simulada.")

    monkeypatch.setattr(repositorio, "salvar", falhar)
    lote = nucleo.preparar_cadastro(dados())
    with pytest.raises(ErroPersistencia):
        nucleo.confirmar(lote)

    assert armazenamento.listar() == ()
    assert armazenamento.buscar_periodo(date(2026, 1, 1), date(2026, 12, 31)) == ()
    assert repositorio.caminho.read_bytes() == antes


def test_composicao_concreta_habilita_rotas_sem_criar_contas(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    RepositorioOcorrenciasJSON(caminho).inicializar()
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-isolada-de-teste",
        "CONTAS_HABILITADAS": True,
        "OCORRENCIAS_HABILITADAS": True,
        "OCORRENCIAS_JSON": caminho,
        "CONTAS_JSON": tmp_path / "contas.json",
        "FOTOS_DIRETORIO": tmp_path / "fotos",
    })

    assert "ocorrencias" in app.extensions
    assert app.test_client().get("/ocorrencias").status_code == 200
    assert app.test_client().get("/login").status_code == 200
    assert not (tmp_path / "contas.json").exists()


def test_composicao_concreta_nao_inicializa_arquivo_ausente(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    with pytest.raises(ErroPersistencia):
        create_app({
            "SECRET_KEY": "chave-isolada-de-teste",
            "CONTAS_HABILITADAS": True,
            "OCORRENCIAS_HABILITADAS": True,
            "OCORRENCIAS_JSON": caminho,
            "CONTAS_JSON": tmp_path / "contas.json",
        })
    assert not caminho.exists()
