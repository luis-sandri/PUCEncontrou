"""Fluxos reais do módulo experimental de Luís, com SQLite temporário."""

import pytest

from app import create_app
from app.erros import ErroPersistencia


pytestmark = pytest.mark.integracao

SENHA = "Senha-ficticia-123!"
NOVA_SENHA = "Outra-senha-ficticia-456!"


@pytest.fixture
def contas_app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "chave-isolada-dos-testes-de-contas",
            "CONTAS_HABILITADAS": True,
            "CONTAS_SQLITE": tmp_path / "contas.sqlite3",
            "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json",
            "SESSION_COOKIE_SECURE": False,
        }
    )
    resultado = app.test_cli_runner().invoke(
        args=["contas", "inicializar"],
        input=f"Admin de teste\nadmin.fixture\n{SENHA}\n{SENHA}\n",
    )
    assert resultado.exit_code == 0, resultado.output
    return app


def _entrar(client, identificador="admin.fixture", senha=SENHA):
    csrf = client.get("/login").get_json()["csrf_token"]
    resposta = client.post(
        "/login",
        json={"identificador": identificador, "senha": senha},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    return resposta.get_json()["csrf_token"]


def _criar_secretario(client, csrf, identificador="secretario.fixture"):
    resposta = client.post(
        "/contas/secretarios",
        json={"nome": "Secretário de teste", "identificador": identificador, "senha": SENHA},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 201, resposta.get_data(as_text=True)
    return resposta.get_json()["conta"]


def _copiar_cookie(app, origem, destino):
    nome = app.config["SESSION_COOKIE_NAME"]
    cookie = origem.get_cookie(nome)
    assert cookie is not None
    destino.set_cookie(nome, cookie.value)


def test_cadastro_consulta_edicao_e_dto_sem_credenciais(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    conta = _criar_secretario(client, csrf)
    assert set(conta) == {"id", "nome", "identificador", "perfil", "ativa"}
    assert conta["perfil"] == "SECRETARIO"
    assert conta["ativa"] is True
    resposta = client.patch(
        f"/contas/secretarios/{conta['id']}",
        json={"nome": "Nome revisado", "identificador": "Revisado.Fixture"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200
    atualizada = resposta.get_json()["conta"]
    assert atualizada["nome"] == "Nome revisado"
    assert atualizada["identificador"] == "revisado.fixture"
    listagem = client.get("/contas/secretarios")
    assert listagem.status_code == 200
    assert listagem.get_json()["contas"] == [atualizada]
    assert SENHA not in listagem.get_data(as_text=True)
    assert "senha_hash" not in listagem.get_data(as_text=True)
    assert not contas_app.config["OCORRENCIAS_JSON"].exists()


def test_anonimo_e_secretario_nao_gerenciam_contas(contas_app):
    admin = contas_app.test_client()
    csrf_admin = _entrar(admin)
    conta = _criar_secretario(admin, csrf_admin)
    anonimo = contas_app.test_client()
    csrf_anonimo = anonimo.get("/login").get_json()["csrf_token"]
    assert anonimo.get("/contas/secretarios").status_code == 401
    assert anonimo.post(
        "/contas/secretarios",
        json={"nome": "Teste", "identificador": "novo.fixture", "senha": SENHA},
        headers={"X-CSRF-Token": csrf_anonimo},
    ).status_code == 401
    secretario = contas_app.test_client()
    csrf = _entrar(secretario, conta["identificador"])
    assert secretario.get("/contas/secretarios").status_code == 403
    assert secretario.patch(
        f"/contas/secretarios/{conta['id']}",
        json={"nome": "Alteração indevida"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 403


def test_csrf_login_ausente_de_outro_cliente_e_rotacionado(contas_app):
    client = contas_app.test_client()
    outro = contas_app.test_client()
    csrf_antigo = client.get("/login").get_json()["csrf_token"]
    csrf_outro = outro.get("/login").get_json()["csrf_token"]
    dados = {"identificador": "admin.fixture", "senha": SENHA}
    assert client.post("/login", json=dados).status_code == 403
    assert client.post(
        "/login", json=dados, headers={"X-CSRF-Token": csrf_outro}
    ).status_code == 403
    resposta = client.post(
        "/login", json=dados, headers={"X-CSRF-Token": csrf_antigo}
    )
    assert resposta.status_code == 200
    csrf_novo = resposta.get_json()["csrf_token"]
    assert csrf_novo != csrf_antigo
    assert client.post(
        "/logout", headers={"X-CSRF-Token": csrf_antigo}
    ).status_code == 403
    assert client.get("/sessao").status_code == 200
    assert client.post("/logout").status_code == 403
    assert client.post(
        "/logout", headers={"X-CSRF-Token": csrf_novo}
    ).status_code == 204


def test_logout_revoga_cookie_copiado_no_servidor(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    replay = contas_app.test_client()
    _copiar_cookie(contas_app, client, replay)
    assert replay.get("/sessao").status_code == 200
    assert client.post(
        "/logout", headers={"X-CSRF-Token": csrf}
    ).status_code == 204
    assert client.get("/sessao").status_code == 401
    assert replay.get("/sessao").status_code == 401


@pytest.mark.parametrize("alteracao", [{"ativa": False}, {"senha": NOVA_SENHA}])
def test_desativacao_e_reset_revogam_todas_as_sessoes(contas_app, alteracao):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    conta = _criar_secretario(admin, csrf)
    primeiro = contas_app.test_client()
    segundo = contas_app.test_client()
    _entrar(primeiro, conta["identificador"])
    _entrar(segundo, conta["identificador"])
    replay = contas_app.test_client()
    _copiar_cookie(contas_app, primeiro, replay)
    assert admin.patch(
        f"/contas/secretarios/{conta['id']}",
        json=alteracao,
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    for client in (primeiro, segundo, replay):
        assert client.get("/sessao").status_code == 401
    novo = contas_app.test_client()
    token = novo.get("/login").get_json()["csrf_token"]
    assert novo.post(
        "/login",
        json={"identificador": conta["identificador"], "senha": SENHA},
        headers={"X-CSRF-Token": token},
    ).status_code == 401
    if "senha" in alteracao:
        _entrar(novo, conta["identificador"], NOVA_SENHA)


def test_falha_por_identificador_duplicado_nao_troca_senha_nem_revoga_sessao(contas_app):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    primeira = _criar_secretario(admin, csrf)
    segunda = _criar_secretario(admin, csrf, "outro.fixture")
    secretario = contas_app.test_client()
    _entrar(secretario, primeira["identificador"])
    resposta = admin.patch(
        f"/contas/secretarios/{primeira['id']}",
        json={"identificador": segunda["identificador"], "senha": NOVA_SENHA},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 409
    assert secretario.get("/sessao").status_code == 200
    _entrar(contas_app.test_client(), primeira["identificador"], SENHA)


@pytest.mark.parametrize("extra", [{"perfil": "ADMINISTRADOR"}, {"ator": "admin.fixture"}, {"senha_hash": "injetado"}])
def test_payload_nao_concede_permissoes_nem_aceita_hash(contas_app, extra):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    resposta = admin.post(
        "/contas/secretarios",
        json={"nome": "Teste", "identificador": "novo.fixture", "senha": SENHA, **extra},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 400
    assert admin.get("/contas/secretarios").get_json()["contas"] == []


def test_erros_de_entrada_e_alvo_inexistente(contas_app):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    headers = {"X-CSRF-Token": csrf}
    assert admin.post(
        "/contas/secretarios", json=["nao-e-objeto"], headers=headers
    ).status_code == 400
    assert admin.post(
        "/contas/secretarios", data="{", content_type="application/json", headers=headers
    ).status_code == 400
    assert admin.post(
        "/contas/secretarios", data="nome=Teste", headers=headers
    ).status_code == 415
    assert admin.patch(
        "/contas/secretarios/id-inexistente", json={"nome": "Teste"}, headers=headers
    ).status_code == 404


@pytest.mark.parametrize("operacao", ["cadastro", "reset"])
def test_senha_unicode_invalida_nao_grava_nem_revoga_sessao(contas_app, operacao):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    conta = _criar_secretario(admin, csrf)
    secretario = contas_app.test_client()
    _entrar(secretario, conta["identificador"])
    headers = {"X-CSRF-Token": csrf}
    # JSON permite a sequência escapada, mas ela não representa texto UTF-8 válido.
    senha_invalida = "\ud800" * 12
    if operacao == "cadastro":
        resposta = admin.post(
            "/contas/secretarios",
            json={
                "nome": "Conta inválida",
                "identificador": "invalida.fixture",
                "senha": senha_invalida,
            },
            headers=headers,
        )
    else:
        resposta = admin.patch(
            f"/contas/secretarios/{conta['id']}",
            json={"nome": "Nome que não deve ser gravado", "senha": senha_invalida},
            headers=headers,
        )
    assert resposta.status_code == 400
    assert admin.get("/contas/secretarios").get_json()["contas"] == [conta]
    assert secretario.get("/sessao").status_code == 200
    _entrar(contas_app.test_client(), conta["identificador"], SENHA)


def test_falha_de_login_nao_revela_se_identificador_existe(contas_app):
    respostas = []
    for identificador in ("admin.fixture", "inexistente.fixture"):
        client = contas_app.test_client()
        csrf = client.get("/login").get_json()["csrf_token"]
        resposta = client.post(
            "/login",
            json={"identificador": identificador, "senha": "Senha-incorreta-123!"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resposta.status_code == 401
        respostas.append(resposta.get_json())
    assert respostas[0] == respostas[1]


def test_erro_de_persistencia_publico_nao_expoe_caminho_ou_detalhes(contas_app, monkeypatch):
    client = contas_app.test_client()
    _entrar(client)

    def falhar(*, ator):
        raise ErroPersistencia("/pasta/privada/banco.sqlite3: SQL e dados internos")

    monkeypatch.setattr(contas_app.extensions["contas"], "listar_secretarios", falhar)
    resposta = client.get("/contas/secretarios")
    assert resposta.status_code == 503
    assert set(resposta.get_json()) == {"erro"}
    assert "sqlite" not in resposta.get_data(as_text=True).lower()
    assert "privada" not in resposta.get_data(as_text=True)


def test_modulo_nao_habilita_ocorrencias_ou_cadastro_publico_de_admin(contas_app):
    client = contas_app.test_client()
    for caminho in ("/ocorrencias", "/contas/administradores"):
        assert client.get(caminho).status_code == 404


def test_cookie_so_contem_tokens_e_respostas_nao_sao_cacheadas(contas_app):
    client = contas_app.test_client()
    resposta = client.get("/login")
    assert "HttpOnly" in resposta.headers["Set-Cookie"]
    assert "SameSite=Lax" in resposta.headers["Set-Cookie"]
    _entrar(client)
    resposta = client.get("/sessao")
    assert resposta.headers["Cache-Control"] == "no-store"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    with client.session_transaction() as sessao:
        assert set(sessao) == {"_permanent", "conta_token", "csrf_token"}
        assert len(sessao["conta_token"]) == 43
        assert resposta.get_json()["conta"]["id"] not in sessao.values()


def test_corpo_excessivo_e_rejeitado_sem_criar_conta(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    resposta = client.post(
        "/contas/secretarios",
        json={"nome": "x" * (17 * 1024)},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 413
    assert client.get("/contas/secretarios").get_json()["contas"] == []

