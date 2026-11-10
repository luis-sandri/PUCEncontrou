import json
from datetime import date

import pytest

from app.erros import ErroPersistencia, ErroValidacao
from app.models.ocorrencia import Ocorrencia
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON


def registro(**alteracoes):
    dados = {
        "tipo": "PERDIDO",
        "nome": "Chaves",
        "categoria": "Acessórios",
        "data_ocorrencia": date(2026, 11, 10),
        "local_ocorrencia": "Biblioteca",
        "foto_referencia": "ocorrencias/foto.jpg",
    }
    dados.update(alteracoes)
    return Ocorrencia.criar(dados)


def test_snapshot_json_preserva_campos_e_vinculos(tmp_path):
    caminho = tmp_path / "dados" / "ocorrencias.json"
    repositorio = RepositorioOcorrenciasJSON(caminho)
    perdido = registro()
    encontrado = registro(
        tipo="ENCONTRADO",
        situacao_guarda="EM_SETOR",
        setor_guarda="Bloco 2",
    )
    from dataclasses import replace

    perdido = replace(perdido, vinculo_id=encontrado.id)
    encontrado = replace(encontrado, vinculo_id=perdido.id)

    repositorio.salvar((perdido, encontrado))

    carregado = RepositorioOcorrenciasJSON(caminho).carregar()
    assert carregado == (perdido, encontrado)
    assert json.loads(caminho.read_text(encoding="utf-8"))["versao"] == 1


def test_leitura_de_arquivo_ausente_falha_explicitamente(tmp_path):
    repositorio = RepositorioOcorrenciasJSON(tmp_path / "ausente.json")
    with pytest.raises(ErroPersistencia, match="ler o arquivo"):
        repositorio.carregar()


def test_inicializacao_cria_vazio_e_nao_substitui_arquivo_existente(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repositorio = RepositorioOcorrenciasJSON(caminho)

    repositorio.inicializar()
    original = caminho.read_bytes()
    repositorio.inicializar()

    assert repositorio.carregar() == ()
    assert caminho.read_bytes() == original


def test_arquivo_invalido_nao_e_sobrescrito_por_inicializacao(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    caminho.write_text('{"versao":99,"ocorrencias":[]}', encoding="utf-8")
    original = caminho.read_bytes()

    with pytest.raises(ErroPersistencia):
        RepositorioOcorrenciasJSON(caminho).inicializar()

    assert caminho.read_bytes() == original


def test_snapshot_invalido_nao_e_persistido(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repositorio = RepositorioOcorrenciasJSON(caminho)
    repositorio.inicializar()
    original = caminho.read_bytes()

    with pytest.raises(ErroValidacao):
        repositorio.salvar((object(),))

    assert caminho.read_bytes() == original


def test_falha_de_replace_preserva_snapshot_anterior(tmp_path, monkeypatch):
    caminho = tmp_path / "ocorrencias.json"
    repositorio = RepositorioOcorrenciasJSON(caminho)
    repositorio.salvar((registro(),))
    original = caminho.read_bytes()

    def falhar_replace(*args):
        raise OSError("falha simulada")

    monkeypatch.setattr("app.repositories.json_ocorrencias.os.replace", falhar_replace)
    with pytest.raises(ErroPersistencia, match="salvar"):
        repositorio.salvar((registro(nome="Mochila"),))

    assert caminho.read_bytes() == original
