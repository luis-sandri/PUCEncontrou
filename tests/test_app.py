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
    assert not app.config["CONTAS_JSON"].exists()


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


def test_contas_desabilitadas_por_padrao(monkeypatch, tmp_path):
    monkeypatch.delenv("PUC_CONTAS_HABILITADAS", raising=False)
    instancia = create_app({
        "SECRET_KEY": "chave-isolada-de-teste",
        "CONTAS_JSON": tmp_path / "contas.json",
    })
    assert instancia.config["CONTAS_HABILITADAS"] is False
    assert "autenticacao" not in instancia.extensions
    assert instancia.test_client().get("/login").status_code == 404
    assert not instancia.config["CONTAS_JSON"].exists()


def test_contas_habilitadas_aguardam_bootstrap_sem_criar_dados(tmp_path):
    instancia = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-isolada-de-teste",
        "CONTAS_HABILITADAS": True,
        "CONTAS_JSON": tmp_path / "dados" / "contas.json",
    })
    assert not instancia.config["CONTAS_JSON"].exists()
    client = instancia.test_client()
    import re
    csrf = re.search(r'name="csrf_token" value="([^" ]+)"', client.get("/login").get_data(as_text=True)).group(1)
    resposta = client.post(
        "/login",
        data={"identificador": "admin@pucpr.edu.br", "senha": "Senha-ficticia-123!", "csrf_token": csrf},
    )
    assert resposta.status_code == 503
    assert not instancia.config["CONTAS_JSON"].parent.exists()


def test_fabricas_contas_nao_compartilham_servicos_ou_dados(tmp_path):
    from app.erros import ErroPersistencia

    primeira, segunda = [create_app({
        "SECRET_KEY": "chave-isolada-de-teste",
        "CONTAS_HABILITADAS": True,
        "CONTAS_JSON": tmp_path / nome / "contas.json",
    }) for nome in ("primeira", "segunda")]
    assert primeira.extensions["contas"] is not segunda.extensions["contas"]
    primeira.extensions["autenticacao"].inicializar_administrador(
        {"nome": "Administrador fictício", "identificador": "admin@pucpr.edu.br"},
        "Senha-ficticia-123!",
    )
    with pytest.raises(ErroPersistencia):
        segunda.extensions["autenticacao"].autenticar("admin@pucpr.edu.br", "Senha-ficticia-123!")
    assert not segunda.config["CONTAS_JSON"].exists()


@pytest.mark.parametrize("duracao", [0, -1, True, "1800"])
def test_duracao_sessao_invalida_na_fabrica(tmp_path, duracao):
    with pytest.raises(ValueError):
        create_app({
            "SECRET_KEY": "chave-isolada-de-teste", "CONTAS_HABILITADAS": True,
            "CONTAS_JSON": tmp_path / "contas.json",
            "CONTAS_DURACAO_SESSAO_SEGUNDOS": duracao,
        })
    assert not (tmp_path / "contas.json").exists()
