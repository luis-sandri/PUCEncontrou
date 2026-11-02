"""Rotas reais de Luís, contas JSON reais e núcleo fake exclusivo dos testes."""

from datetime import date
from io import BytesIO

from PIL import Image
import pytest

from app import create_app
from app.composicao import DependenciasOcorrencias
from app.erros import ConflitoAlteracao, ErroPersistencia
from app.models.ocorrencia import StatusOcorrencia
from tests.fakes_ocorrencias import ConsultaFake, criar_nucleo
from tests.integration.test_contas_http import Pagina, _entrar

pytestmark = pytest.mark.integracao
SENHA = "Senha-ficticia-123!"


def imagem():
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def contexto(tmp_path):
    nucleo = criar_nucleo()
    consulta = ConsultaFake(nucleo)
    app = create_app({
        "TESTING": True, "SECRET_KEY": "chave-isolada-de-teste",
        "CONTAS_HABILITADAS": True, "OCORRENCIAS_HABILITADAS": True,
        "OCORRENCIAS_COMPOSITOR": lambda config: DependenciasOcorrencias(nucleo, consulta),
        "CONTAS_JSON": tmp_path / "contas.json", "FOTOS_DIRETORIO": tmp_path / "fotos",
        "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json", "SESSION_COOKIE_SECURE": False,
    })
    admin = app.extensions["autenticacao"].inicializar_administrador(
        {"nome": "Admin fictício", "identificador": "admin@pucpr.edu.br"}, SENHA,
    )
    secretario = app.extensions["contas"].cadastrar_secretario(
        {"nome": "Secretário fictício", "identificador": "secretario@pucpr.edu.br"}, SENHA, ator=admin,
    )
    return app, nucleo, consulta, admin, secretario


def csrf(client, caminho="/ocorrencias/nova"):
    return Pagina(client.get(caminho, follow_redirects=True)).csrf


def cadastrar(client, **campos):
    valores = {
        "csrf_token": csrf(client), "tipo": "PERDIDO", "nome": "Garrafa fictícia",
        "categoria": "Categoria teste", "data_ocorrencia": "2026-10-01",
        "local_ocorrencia": "Local fictício", "foto": (BytesIO(imagem()), "../../nome-inseguro.png"),
        **campos,
    }
    resposta = client.post("/ocorrencias/nova", data=valores)
    assert resposta.status_code == 303, resposta.get_data(as_text=True)
    return resposta.location.rsplit("/", 1)[1]


def test_cadastro_consulta_detalhe_e_foto_publicos(contexto):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    identificador = cadastrar(client, tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Secretaria fictícia")
    resposta = client.get("/ocorrencias/" + identificador)
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Garrafa fictícia" in html
    assert "Local fictício" in html
    assert "Secretaria fictícia" in html
    assert "nome-inseguro" not in html
    assert nucleo.obter(identificador).foto_referencia not in html
    assert "Ações da secretaria" not in html
    foto = client.get(f"/ocorrencias/{identificador}/foto")
    assert foto.status_code == 200
    assert foto.mimetype == "image/png"
    assert foto.data == imagem()
    assert "no-store" in foto.headers["Cache-Control"]
    assert not app.config["OCORRENCIAS_JSON"].exists()
    assert "Garrafa fictícia" in client.get("/ocorrencias").get_data(as_text=True)


def test_consulta_combinada_delega_periodo_a_consulta_injetada(contexto):
    app, _, consulta, _, _ = contexto
    client = app.test_client()
    cadastrar(client, nome="Garrafa azul")
    cadastrar(client, nome="Caderno", data_ocorrencia="2026-10-02")
    resposta = client.get("/ocorrencias", query_string={"inicio": "2026-10-01", "fim": "2026-10-01", "tipo": "PERDIDO", "q": "garrafa"})
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Garrafa azul" in html
    assert "Caderno" not in html
    assert consulta.chamadas == [(date(2026, 10, 1), date(2026, 10, 1))]
    assert client.get("/ocorrencias?inicio=2026-10-02&fim=2026-10-01").status_code == 400
    assert client.get("/ocorrencias?filtro_inventado=1").status_code == 400
    assert "Nenhuma ocorrência" in client.get("/ocorrencias?q=inexistente").get_data(as_text=True)


def test_anonimo_e_administrador_nao_executam_acoes_de_secretario(contexto):
    app, nucleo, _, _, _ = contexto
    anonimo = app.test_client()
    identificador = cadastrar(anonimo)
    assert anonimo.get(f"/ocorrencias/{identificador}/editar").location.endswith("/login")
    assert anonimo.post(f"/ocorrencias/{identificador}/excluir").location.endswith("/login")
    admin = app.test_client()
    token = _entrar(admin)
    assert admin.get(f"/ocorrencias/{identificador}/editar").status_code == 403
    for rota, dados in [
        (f"/{identificador}/editar", {"nome": "Forjado"}),
        (f"/{identificador}/status", {"novo_status": "CANCELADO"}),
        (f"/{identificador}/excluir", {"confirmacao": "sim"}),
        ("/vinculos", {"perdido_id": identificador, "encontrado_id": "outro"}),
    ]:
        assert admin.post("/ocorrencias" + rota, data={"csrf_token": token, **dados}).status_code == 403
    assert nucleo.obter(identificador).status is StatusOcorrencia.ABERTO


def test_secretario_edita_sem_trocar_foto_e_exige_csrf(contexto):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    identificador = cadastrar(client)
    antiga = nucleo.obter(identificador).foto_referencia
    token = _entrar(client, "secretario@pucpr.edu.br")
    assert client.post(f"/ocorrencias/{identificador}/editar", data={"nome": "Outro"}).status_code == 403
    resposta = client.post(f"/ocorrencias/{identificador}/editar", data={"csrf_token": token, "nome": "Nome corrigido"})
    assert resposta.status_code == 303
    assert nucleo.obter(identificador).nome == "Nome corrigido"
    assert nucleo.obter(identificador).foto_referencia == antiga
    assert "Ações da secretaria" in client.get(f"/ocorrencias/{identificador}").get_data(as_text=True)


def test_vinculo_devolucao_reabertura_cancelamento_e_exclusao(contexto):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    perdido = cadastrar(client)
    encontrado = cadastrar(client, tipo="ENCONTRADO")
    token = _entrar(client, "secretario@pucpr.edu.br")
    assert client.post("/ocorrencias/vinculos", data={"csrf_token": token, "perdido_id": perdido, "encontrado_id": encontrado}).status_code == 303
    assert nucleo.obter(perdido).status is StatusOcorrencia.ABERTO
    assert nucleo.obter(encontrado).status is StatusOcorrencia.ABERTO
    url = f"/ocorrencias/{perdido}/status"
    assert client.post(url, data={"csrf_token": token, "novo_status": "RESOLVIDO"}).status_code == 400
    assert client.post(url, data={"csrf_token": token, "novo_status": "RESOLVIDO", "confirmacao_presencial": "sim"}).status_code == 303
    assert all(nucleo.obter(i).status is StatusOcorrencia.RESOLVIDO for i in (perdido, encontrado))
    assert client.post(url, data={"csrf_token": token, "novo_status": "ABERTO"}).status_code == 303
    assert all(nucleo.obter(i).status is StatusOcorrencia.ABERTO for i in (perdido, encontrado))
    assert client.post(url, data={"csrf_token": token, "novo_status": "CANCELADO"}).status_code == 400
    assert client.post(f"/ocorrencias/{perdido}/excluir", data={"csrf_token": token}).status_code == 400
    assert client.post(f"/ocorrencias/{perdido}/excluir", data={"csrf_token": token, "confirmacao": "sim"}).status_code == 303
    assert client.get(f"/ocorrencias/{perdido}").status_code == 404
    assert client.get(f"/ocorrencias/{perdido}/foto").status_code == 404
    assert nucleo.obter(encontrado).vinculo_id is None
    assert nucleo.obter(encontrado).status is StatusOcorrencia.ABERTO
    assert client.post(f"/ocorrencias/{encontrado}/status", data={"csrf_token": token, "novo_status": "CANCELADO"}).status_code == 303


@pytest.mark.parametrize("extra", [{"id": "forjado"}, {"status": "RESOLVIDO"}, {"ator": "secretario"}, {"foto_referencia": "../segredo"}])
def test_cadastro_rejeita_campos_controlados(contexto, extra):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    resposta = client.post("/ocorrencias/nova", data={
        "csrf_token": csrf(client), "tipo": "PERDIDO", "nome": "Teste", "categoria": "Teste",
        "local_ocorrencia": "Teste", "data_ocorrencia": "2026-10-01",
        "foto": (BytesIO(imagem()), "teste.png"), **extra,
    })
    assert resposta.status_code == 400
    assert tuple(nucleo.listar()) == ()
    assert not app.config["FOTOS_DIRETORIO"].exists()


@pytest.mark.parametrize("foto", [None, b"<html>falso</html>", b"x" * 1_500_001])
def test_foto_obrigatoria_valida_e_com_limite(contexto, foto):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    dados = {"csrf_token": csrf(client), "tipo": "PERDIDO", "nome": "Teste", "categoria": "Teste", "local_ocorrencia": "Teste", "data_ocorrencia": "2026-10-01"}
    if foto is not None:
        dados["foto"] = (BytesIO(foto), "falso.jpg")
    resposta = client.post("/ocorrencias/nova", data=dados)
    assert resposta.status_code == 400
    assert tuple(nucleo.listar()) == ()
    assert not app.config["FOTOS_DIRETORIO"].exists()


def test_falha_e_conflito_nao_expoem_caminhos_e_descartam_nova_foto(contexto, monkeypatch):
    app, nucleo, _, _, _ = contexto
    client = app.test_client()
    def falhar(lote):
        raise ErroPersistencia("/pasta/privada/ocorrencias.json")
    monkeypatch.setattr(nucleo, "confirmar", falhar)
    resposta = client.post("/ocorrencias/nova", data={
        "csrf_token": csrf(client), "tipo": "PERDIDO", "nome": "Teste", "categoria": "Teste", "local_ocorrencia": "Teste", "data_ocorrencia": "2026-10-01", "foto": (BytesIO(imagem()), "teste.png"),
    })
    assert resposta.status_code == 503
    assert "pasta/privada" not in resposta.get_data(as_text=True)
    assert list(app.config["FOTOS_DIRETORIO"].rglob("*.png")) == []
    def conflito(lote):
        raise ConflitoAlteracao("Atualize e tente novamente.")
    monkeypatch.setattr(nucleo, "confirmar", conflito)
    resposta = client.post("/ocorrencias/nova", data={
        "csrf_token": csrf(client), "tipo": "PERDIDO", "nome": "Teste", "categoria": "Teste", "local_ocorrencia": "Teste", "data_ocorrencia": "2026-10-01", "foto": (BytesIO(imagem()), "teste.png"),
    })
    assert resposta.status_code == 409


def test_secretario_desativado_perde_acesso(contexto):
    app, nucleo, _, admin, secretario = contexto
    client = app.test_client()
    identificador = cadastrar(client)
    token = _entrar(client, "secretario@pucpr.edu.br")
    app.extensions["contas"].gerenciar_secretario(secretario.id, {"ativa": False}, ator=admin)
    resposta = client.post(f"/ocorrencias/{identificador}/status", data={"csrf_token": token, "novo_status": "CANCELADO"})
    assert resposta.location.endswith("/login")
    assert nucleo.obter(identificador).status is StatusOcorrencia.ABERTO
