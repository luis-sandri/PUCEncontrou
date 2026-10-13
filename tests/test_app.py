"""Somente inicialização, isolamento e superfície HTTP da base."""

import pytest

from app import create_app


def test_inicio_renderiza_template(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "PUC Encontrou" in response.get_data(as_text=True)


def test_criacao_nao_acessa_persistencia(app):
    assert not app.config["OCORRENCIAS_JSON"].exists()
    assert not app.config["CONTAS_SQLITE"].exists()


def test_fabrica_cria_instancias_independentes():
    primeira = create_app({"SECRET_KEY": "primeira-chave-de-teste"})
    segunda = create_app({"SECRET_KEY": "segunda-chave-de-teste"})
    assert primeira is not segunda
    assert primeira.config["SECRET_KEY"] != segunda.config["SECRET_KEY"]


def test_sem_chave_externa_falha_na_inicializacao(monkeypatch):
    monkeypatch.delenv("PUC_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PUC_SECRET_KEY"):
        create_app()


def test_configuracao_le_ambiente_em_cada_instancia(monkeypatch, tmp_path):
    monkeypatch.setenv("PUC_SECRET_KEY", "chave-de-teste-do-ambiente")
    monkeypatch.setenv("PUC_OCORRENCIAS_JSON", str(tmp_path / "teste.json"))
    monkeypatch.setenv("PUC_SESSION_COOKIE_SECURE", "true")
    instancia = create_app()
    assert instancia.config["OCORRENCIAS_JSON"] == tmp_path / "teste.json"
    assert instancia.config["SESSION_COOKIE_SECURE"] is True
    monkeypatch.setenv("PUC_SESSION_COOKIE_SECURE", "false")
    assert create_app().config["SESSION_COOKIE_SECURE"] is False


def test_endpoints_de_negocio_ainda_nao_expostos(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    assert endpoints == {"static", "publicas.inicio"}
