"""Formulários reais, sessão Flask e SQLite temporário do módulo de Luís."""

from html.parser import HTMLParser

import pytest

from app import create_app
from app.erros import ErroPersistencia

pytestmark = pytest.mark.integracao
SENHA = "Senha-ficticia-123!"
NOVA_SENHA = "Outra-senha-ficticia-456!"
ADMIN = "admin@pucpr.edu.br"


class Pagina(HTMLParser):
    def __init__(self, resposta):
        super().__init__()
        self.inputs = []
        self.links = set()
        self.feed(resposta.get_data(as_text=True))

    def handle_starttag(self, tag, attrs):
        dados = dict(attrs)
        if tag == "input":
            self.inputs.append(dados)
        if tag == "a":
            self.links.add(dados.get("href", ""))

    @property
    def csrf(self):
        return next(item["value"] for item in self.inputs if item.get("name") == "csrf_token")


@pytest.fixture
def contas_app(tmp_path):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "chave-isolada-dos-testes-de-contas",
        "CONTAS_HABILITADAS": True, "CONTAS_SQLITE": tmp_path / "contas.sqlite3",
        "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json", "SESSION_COOKIE_SECURE": False,
    })
    resultado = app.test_cli_runner().invoke(
        args=["contas", "inicializar"], input=f"Admin de teste\n{ADMIN}\n{SENHA}\n{SENHA}\n",
    )
    assert resultado.exit_code == 0, resultado.output
    return app


def _csrf(client, caminho="/login"):
    return Pagina(client.get(caminho, follow_redirects=True)).csrf


def _entrar(client, identificador=ADMIN, senha=SENHA):
    resposta = client.post("/login", data={
        "csrf_token": _csrf(client), "identificador": identificador, "senha": senha,
    })
    assert resposta.status_code == 303, resposta.get_data(as_text=True)
    assert resposta.location.endswith("/sessao")
    return _csrf(client, "/sessao")


def _criar(client, csrf, email="secretario@pucpr.edu.br"):
    antes = Pagina(client.get("/contas/secretarios")).links
    resposta = client.post("/contas/secretarios", data={
        "csrf_token": csrf, "nome": "Secretário fictício", "identificador": email,
        "senha": SENHA, "confirmacao_senha": SENHA,
    })
    assert resposta.status_code == 303, resposta.get_data(as_text=True)
    depois = Pagina(client.get("/contas/secretarios")).links
    link = next(link for link in depois - antes if link.endswith("/editar"))
    return link.removesuffix("/editar")


def test_fluxo_cadastro_edicao_e_telas_sem_senha(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    caminho = _criar(client, csrf)
    resposta = client.get(caminho + "/editar")
    assert resposta.status_code == 200
    assert "secretario@pucpr.edu.br" in resposta.get_data(as_text=True)
    assert SENHA not in resposta.get_data(as_text=True)
    assert "senha_hash" not in resposta.get_data(as_text=True)
    assert all(not campo.get("value") for campo in Pagina(resposta).inputs if campo.get("type") == "password")
    resposta = client.post(caminho + "/editar", data={
        "csrf_token": csrf, "nome": "Nome revisado", "identificador": "NOVO@PUCPR.EDU.BR",
    }, follow_redirects=True)
    assert resposta.status_code == 200
    assert "Nome revisado" in resposta.get_data(as_text=True)
    assert "novo@pucpr.edu.br" in resposta.get_data(as_text=True)
    assert not contas_app.config["OCORRENCIAS_JSON"].exists()


def test_anonimo_e_secretario_nao_gerenciam_contas(contas_app):
    admin = contas_app.test_client()
    caminho = _criar(admin, _entrar(admin))
    anonimo = contas_app.test_client()
    assert anonimo.get("/contas/secretarios").location.endswith("/login")
    assert anonimo.post(caminho + "/situacao", data={"ativa": "true"}).location.endswith("/login")
    secretario = contas_app.test_client()
    csrf = _entrar(secretario, "secretario@pucpr.edu.br")
    assert secretario.get("/contas/secretarios").status_code == 403
    for acao, dados in [("editar", {"nome": "Outro"}), ("situacao", {"ativa": "false"}), ("senha", {"senha": SENHA, "confirmacao_senha": SENHA})]:
        assert secretario.post(caminho + "/" + acao, data={"csrf_token": csrf, **dados}).status_code == 403


def test_csrf_ausente_de_outro_cliente_e_rotacao_no_login(contas_app):
    client, outro = contas_app.test_client(), contas_app.test_client()
    antigo = _csrf(client)
    dados = {"identificador": ADMIN, "senha": SENHA}
    assert client.post("/login", data=dados).status_code == 403
    assert client.post("/login", data={**dados, "csrf_token": _csrf(outro)}).status_code == 403
    assert client.post("/login", data={**dados, "csrf_token": antigo}).status_code == 303
    novo = _csrf(client, "/sessao")
    assert novo != antigo
    assert client.post("/logout", data={"csrf_token": antigo}).status_code == 403
    assert client.post("/logout", data={"csrf_token": novo}).status_code == 303
    assert client.get("/sessao").location.endswith("/login")


@pytest.mark.parametrize("acao,dados", [
    ("situacao", {"ativa": "false"}),
    ("senha", {"senha": NOVA_SENHA, "confirmacao_senha": NOVA_SENHA}),
])
def test_desativacao_e_reset_invalidam_sessoes_em_outros_clientes(contas_app, acao, dados):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    caminho = _criar(admin, csrf)
    primeiro, segundo = contas_app.test_client(), contas_app.test_client()
    _entrar(primeiro, "secretario@pucpr.edu.br")
    _entrar(segundo, "secretario@pucpr.edu.br")
    assert admin.post(caminho + "/" + acao, data={"csrf_token": csrf, **dados}).status_code == 303
    for client in (primeiro, segundo):
        assert client.get("/sessao").location.endswith("/login")
    assert primeiro.post("/login", data={
        "csrf_token": _csrf(primeiro), "identificador": "secretario@pucpr.edu.br", "senha": SENHA,
    }).status_code == 401
    if acao == "senha":
        _entrar(primeiro, "secretario@pucpr.edu.br", NOVA_SENHA)
    else:
        assert admin.post(caminho + "/situacao", data={"csrf_token": csrf, "ativa": "true"}).status_code == 303
        _entrar(primeiro, "secretario@pucpr.edu.br")


def test_expiracao_absoluta_e_cookie_sem_credenciais(contas_app, monkeypatch):
    client = contas_app.test_client()
    _entrar(client)
    with client.session_transaction() as sessao:
        expira_em = sessao["expira_em"]
        assert set(sessao) == {"_permanent", "conta_id", "versao_sessao", "expira_em", "csrf_token"}
        assert SENHA not in sessao.values()
    monkeypatch.setattr("app.routes.seguranca.time.time", lambda: expira_em)
    assert client.get("/sessao").location.endswith("/login")


@pytest.mark.parametrize("extra", [{"perfil": "ADMINISTRADOR"}, {"ator": "admin"}, {"senha_hash": "injetado"}])
def test_campos_extras_recusados(contas_app, extra):
    client = contas_app.test_client()
    csrf = _entrar(client)
    resposta = client.post("/contas/secretarios", data={
        "csrf_token": csrf, "nome": "Teste", "identificador": "novo@pucpr.edu.br",
        "senha": SENHA, "confirmacao_senha": SENHA, **extra,
    })
    assert resposta.status_code == 400
    assert "Nenhum secretário" in client.get("/contas/secretarios").get_data(as_text=True)


def test_erro_preserva_campos_seguros_e_escapa_html(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    resposta = client.post("/contas/secretarios", data={
        "csrf_token": csrf, "nome": '<script>alert("x")</script>', "identificador": "invalido@gmail.com",
        "senha": SENHA, "confirmacao_senha": SENHA,
    })
    assert resposta.status_code == 400
    html = resposta.get_data(as_text=True)
    assert "@pucpr.edu.br" in html
    assert "invalido@gmail.com" in html
    assert "<script>alert" not in html
    assert SENHA not in html
    assert "&lt;script&gt;" in html


def test_duplicidade_nao_altera_credenciais_nem_invalida_sessao(contas_app):
    admin = contas_app.test_client()
    csrf = _entrar(admin)
    caminho = _criar(admin, csrf)
    _criar(admin, csrf, "ocupado@pucpr.edu.br")
    secretario = contas_app.test_client()
    _entrar(secretario, "secretario@pucpr.edu.br")
    resposta = admin.post(caminho + "/editar", data={
        "csrf_token": csrf, "nome": "Outro", "identificador": "ocupado@pucpr.edu.br",
    })
    assert resposta.status_code == 409
    assert secretario.get("/sessao").status_code == 200
    _entrar(contas_app.test_client(), "secretario@pucpr.edu.br")


def test_confirmacao_senha_incorreta_nao_grava(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    resposta = client.post("/contas/secretarios", data={
        "csrf_token": csrf, "nome": "Teste", "identificador": "novo@pucpr.edu.br",
        "senha": SENHA, "confirmacao_senha": "Diferente-123456!",
    })
    assert resposta.status_code == 400
    assert "não confere" in resposta.get_data(as_text=True)
    assert "Nenhum secretário" in client.get("/contas/secretarios").get_data(as_text=True)


def test_persistencia_indisponivel_nao_expoe_detalhes(contas_app, monkeypatch):
    client = contas_app.test_client()
    _entrar(client)
    def falhar(*, ator):
        raise ErroPersistencia("/pasta/privada/banco.sqlite3: SQL interno")
    monkeypatch.setattr(contas_app.extensions["contas"], "listar_secretarios", falhar)
    resposta = client.get("/contas/secretarios")
    assert resposta.status_code == 503
    assert "privada" not in resposta.get_data(as_text=True)
    assert "SQL interno" not in resposta.get_data(as_text=True)


def test_corpo_excessivo_e_contrato_html(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    resposta = client.post("/contas/secretarios", data={"csrf_token": csrf, "nome": "x" * 17000})
    assert resposta.status_code == 413
    resposta = client.get("/contas/secretarios")
    assert resposta.mimetype == "text/html"
    assert resposta.headers["Cache-Control"] == "no-store"
    assert client.patch("/contas/secretarios/id").status_code == 404
    for caminho in ("/ocorrencias", "/contas/administradores"):
        assert client.get(caminho).status_code == 404


def test_mutacoes_exigem_formulario_post(contas_app):
    client = contas_app.test_client()
    csrf = _entrar(client)
    caminho = _criar(client, csrf)
    for acao in ("situacao", "senha"):
        assert client.get(caminho + "/" + acao).status_code == 405
    assert client.get("/logout").status_code == 405
    assert client.post("/contas/secretarios", json={"csrf_token": csrf}).status_code == 415
    assert client.get("/sessao").status_code == 200
