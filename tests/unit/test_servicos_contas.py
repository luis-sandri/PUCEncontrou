"""Cenários de contas e sessões de Luís com SQLite fictício e isolado."""

from dataclasses import FrozenInstanceError, asdict, replace
import hashlib

import pytest
from werkzeug.security import check_password_hash

from app.erros import (
    ContaNaoEncontrada,
    ErroValidacao,
    FalhaAutenticacao,
    IdentificadorEmUso,
    PermissaoNegada,
)
from app.models.conta import Perfil
from app.repositories.sqlite_contas import RepositorioContasSQLite
from app.services.autenticacao import ServicoAutenticacao
from app.services.contas import ServicoContas

SENHA = "somente-testes-1234"
OUTRA_SENHA = "outra-senha-de-teste-5678"


@pytest.fixture
def contexto(tmp_path):
    repositorio = RepositorioContasSQLite(tmp_path / "contas.sqlite3")
    autenticacao = ServicoAutenticacao(repositorio, duracao_sessao_segundos=60)
    administrador = autenticacao.inicializar_administrador(
        {"nome": "Admin Fictício", "identificador": "admin-teste"}, SENHA
    )
    return repositorio, autenticacao, ServicoContas(repositorio), administrador


def criar_secretario(gestao, administrador, identificador="secretario-teste"):
    return gestao.cadastrar_secretario(
        {"nome": "Secretário Fictício", "identificador": identificador},
        SENHA,
        ator=administrador,
    )


def test_cria_normaliza_e_autentica_sem_expor_hash(contexto):
    repositorio, autenticacao, gestao, administrador = contexto
    conta = criar_secretario(gestao, administrador, "  SECRETARIO-TESTE  ")
    assert conta.identificador == "secretario-teste"
    assert conta.perfil == Perfil.SECRETARIO
    assert set(asdict(conta)) == {"id", "perfil", "nome", "identificador", "ativa"}
    assert autenticacao.autenticar(" SECRETARIO-TESTE ", SENHA) == conta
    credenciais = repositorio.buscar_por_id(conta.id)
    assert check_password_hash(credenciais.senha_hash, SENHA)
    assert credenciais.senha_hash not in repr(credenciais)
    assert SENHA not in repr(conta)
    with pytest.raises(FrozenInstanceError):
        conta.nome = "Nome alterado por fora"


def test_identificador_unico_apos_normalizacao(contexto):
    _, _, gestao, administrador = contexto
    criar_secretario(gestao, administrador)
    with pytest.raises(IdentificadorEmUso):
        criar_secretario(gestao, administrador, " SECRETARIO-TESTE ")


@pytest.mark.parametrize("ator", [None, "usuario-anonimo"])
def test_gestao_recusa_ator_ausente(contexto, ator):
    _, _, gestao, _ = contexto
    with pytest.raises(PermissaoNegada):
        gestao.listar_secretarios(ator=ator)


def test_secretario_nao_ganha_poder_por_perfil_forjado(contexto):
    _, _, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    forjado = replace(secretario, perfil=Perfil.ADMINISTRADOR)
    with pytest.raises(PermissaoNegada):
        gestao.cadastrar_secretario(
            {"nome": "Conta fictícia", "identificador": "tentativa"},
            SENHA,
            ator=forjado,
        )
    with pytest.raises(PermissaoNegada):
        gestao.gerenciar_secretario(secretario.id, {"nome": "Outro"}, ator=forjado)
    with pytest.raises(PermissaoNegada):
        gestao.listar_secretarios(ator=forjado)


def test_id_inexistente_com_perfil_admin_nao_autoriza(contexto):
    _, _, gestao, administrador = contexto
    with pytest.raises(PermissaoNegada):
        gestao.listar_secretarios(ator=replace(administrador, id="inexistente"))


@pytest.mark.parametrize(
    "alteracoes",
    [
        {},
        {"perfil": "ADMINISTRADOR"},
        {"senha_hash": "hash-enviado"},
        {"ativa": True},
        {"ativa": 0},
        {"nome": "Nome válido", "extra": 1},
        {"identificador": "sem espacos"},
        {"senha": "curta"},
    ],
)
def test_alteracoes_invalidas_nao_gravam(contexto, alteracoes):
    repositorio, _, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    antes = repositorio.buscar_por_id(secretario.id)
    with pytest.raises(ErroValidacao):
        gestao.gerenciar_secretario(secretario.id, alteracoes, ator=administrador)
    assert repositorio.buscar_por_id(secretario.id) == antes


def test_validacao_completa_antes_da_gravacao(contexto):
    repositorio, _, gestao, administrador = contexto
    with pytest.raises(ErroValidacao):
        gestao.cadastrar_secretario(
            {"nome": "Teste", "identificador": "novo", "perfil": "ADMINISTRADOR"},
            SENHA,
            ator=administrador,
        )
    with pytest.raises(ErroValidacao):
        gestao.cadastrar_secretario(
            {"nome": "Teste\x00inválido", "identificador": "novo"},
            SENHA,
            ator=administrador,
        )
    assert repositorio.listar_secretarios() == []


def test_edita_conta_e_nao_altera_administrador(contexto):
    _, _, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    editado = gestao.gerenciar_secretario(
        secretario.id,
        {"nome": "  Novo Nome  ", "identificador": "NOVO-LOGIN"},
        ator=administrador,
    )
    assert editado.id == secretario.id
    assert editado.nome == "Novo Nome"
    assert editado.identificador == "novo-login"
    assert gestao.listar_secretarios(ator=administrador) == [editado]
    with pytest.raises(ContaNaoEncontrada):
        gestao.gerenciar_secretario(administrador.id, {"nome": "Outro"}, ator=administrador)


def test_erros_de_login_nao_revelam_causa(contexto):
    _, autenticacao, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    mensagens = []
    for identificador, senha in [
        ("inexistente", SENHA),
        ("secretario-teste", OUTRA_SENHA),
        ("secretario-teste", "curta"),
        (None, SENHA),
    ]:
        with pytest.raises(FalhaAutenticacao) as erro:
            autenticacao.autenticar(identificador, senha)
        mensagens.append(str(erro.value))
    gestao.gerenciar_secretario(secretario.id, {"ativa": False}, ator=administrador)
    with pytest.raises(FalhaAutenticacao) as erro:
        autenticacao.autenticar("secretario-teste", SENHA)
    mensagens.append(str(erro.value))
    assert len(set(mensagens)) == 1


def test_senha_nao_e_cortada_ou_normalizada(contexto):
    _, autenticacao, gestao, administrador = contexto
    senha = "  senha-com-espacos-1234  "
    conta = gestao.cadastrar_secretario(
        {"nome": "Conta Fictícia", "identificador": "espacos"},
        senha,
        ator=administrador,
    )
    assert autenticacao.autenticar("espacos", senha) == conta
    with pytest.raises(FalhaAutenticacao):
        autenticacao.autenticar("espacos", senha.strip())


def test_senha_unicode_invalida_nao_cria_conta(contexto):
    repositorio, _, gestao, administrador = contexto
    with pytest.raises(ErroValidacao, match="Unicode"):
        gestao.cadastrar_secretario(
            {"nome": "Conta Fictícia", "identificador": "unicode-invalido"},
            "\ud800" * 12,
            ator=administrador,
        )
    assert repositorio.buscar_por_identificador("unicode-invalido") is None


def test_reset_unicode_invalido_preserva_credenciais_e_sessao(contexto):
    repositorio, autenticacao, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    _, token = autenticacao.iniciar_sessao("secretario-teste", SENHA)
    antes = repositorio.buscar_por_id(secretario.id)
    with pytest.raises(ErroValidacao, match="Unicode"):
        gestao.gerenciar_secretario(
            secretario.id,
            {"senha": "\ud800" * 12},
            ator=administrador,
        )
    assert repositorio.buscar_por_id(secretario.id) == antes
    assert autenticacao.obter_sessao(token) == secretario
    assert autenticacao.autenticar("secretario-teste", SENHA) == secretario


def test_sessao_hash_expiracao_e_logout(contexto, monkeypatch):
    repositorio, autenticacao, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    monkeypatch.setattr("app.services.autenticacao.time.time", lambda: 1000)
    conta, token = autenticacao.iniciar_sessao("secretario-teste", SENHA)
    assert conta == secretario
    assert len(token) == 43
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    assert repositorio.buscar_sessao(token_hash, 1000).id == secretario.id
    assert repositorio.buscar_sessao(token, 1000) is None
    assert autenticacao.obter_sessao(token) == secretario
    monkeypatch.setattr("app.services.autenticacao.time.time", lambda: 1060)
    assert autenticacao.obter_sessao(token) is None
    monkeypatch.setattr("app.services.autenticacao.time.time", lambda: 1000)
    autenticacao.encerrar_sessao(token)
    assert autenticacao.obter_sessao(token) is None
    assert autenticacao.obter_sessao("token-inválido") is None


def test_reset_revoga_todas_sessoes_e_invalida_senha_anterior(contexto):
    _, autenticacao, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    _, token_um = autenticacao.iniciar_sessao("secretario-teste", SENHA)
    _, token_dois = autenticacao.iniciar_sessao("secretario-teste", SENHA)
    gestao.gerenciar_secretario(secretario.id, {"senha": OUTRA_SENHA}, ator=administrador)
    assert autenticacao.obter_sessao(token_um) is None
    assert autenticacao.obter_sessao(token_dois) is None
    with pytest.raises(FalhaAutenticacao):
        autenticacao.autenticar("secretario-teste", SENHA)
    assert autenticacao.autenticar("secretario-teste", OUTRA_SENHA).id == secretario.id


def test_desativacao_revoga_sessao_e_recusa_login(contexto):
    _, autenticacao, gestao, administrador = contexto
    secretario = criar_secretario(gestao, administrador)
    _, token = autenticacao.iniciar_sessao("secretario-teste", SENHA)
    gestao.gerenciar_secretario(secretario.id, {"ativa": False}, ator=administrador)
    assert autenticacao.obter_sessao(token) is None
    with pytest.raises(FalhaAutenticacao):
        autenticacao.iniciar_sessao("secretario-teste", SENHA)


def test_bootstrap_sem_conta_padrao_e_sem_repeticao(tmp_path):
    caminho = tmp_path / "contas.sqlite3"
    autenticacao = ServicoAutenticacao(RepositorioContasSQLite(caminho))
    assert not caminho.exists()
    admin = autenticacao.inicializar_administrador(
        {"nome": "Admin Fictício", "identificador": "admin-teste"}, SENHA
    )
    assert admin.perfil == Perfil.ADMINISTRADOR
    with pytest.raises(ErroValidacao):
        autenticacao.inicializar_administrador(
            {"nome": "Outro Fictício", "identificador": "outro-admin"}, SENHA
        )


@pytest.mark.parametrize("duracao", [0, -1, True, "1800"])
def test_duracao_sessao_invalida_rejeitada_sem_acesso_banco(tmp_path, duracao):
    with pytest.raises(ValueError):
        ServicoAutenticacao(
            RepositorioContasSQLite(tmp_path / "inexistente.sqlite3"), duracao
        )
