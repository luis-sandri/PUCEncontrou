"""Persistência experimental de contas usando somente dados sintéticos em tmp_path."""

from dataclasses import FrozenInstanceError
from hashlib import sha256
import sqlite3

import pytest

from app.erros import (
    ContaNaoEncontrada,
    ErroPersistencia,
    ErroValidacao,
    FalhaAutenticacao,
    IdentificadorEmUso,
)
from app.models.conta import Perfil
from app.repositories.sqlite_contas import RepositorioContasSQLite


@pytest.fixture
def repositorio(tmp_path):
    repo = RepositorioContasSQLite(tmp_path / "contas.sqlite3")
    repo.inicializar()
    return repo


def dados(identificador="secretario-teste"):
    return {"nome": "Secretário fictício", "identificador": identificador}


def token_hash(token="token-ficticio"):
    return sha256(token.encode()).hexdigest()


def criar_sessao(repo, conta, *, token="token-ficticio", senha_hash="hash-sintetico"):
    repo.criar_sessao(conta.id, token_hash(token), 200, senha_hash_esperada=senha_hash)


def test_construtor_e_consulta_nao_criam_dados(tmp_path):
    caminho = tmp_path / "nao-criado" / "contas.sqlite3"
    repo = RepositorioContasSQLite(caminho)
    assert not caminho.parent.exists()
    with pytest.raises(ErroPersistencia):
        repo.buscar_por_id("ausente")
    assert not caminho.parent.exists()


def test_persiste_reabre_e_separa_visao_de_credenciais(repositorio):
    conta = repositorio.salvar_secretario(dados("  SEC-TÉSTE  "), senha_hash="hash-sintetico")
    assert conta.perfil is Perfil.SECRETARIO
    assert conta.identificador == "sec-téste"
    assert not hasattr(conta, "senha_hash")
    with pytest.raises(FrozenInstanceError):
        conta.nome = "Alteração direta"
    reaberto = RepositorioContasSQLite(repositorio.caminho)
    credenciais = reaberto.buscar_por_identificador(" SEC-TÉSTE ")
    assert credenciais.id == conta.id
    assert credenciais.senha_hash == "hash-sintetico"
    assert "hash-sintetico" not in repr(credenciais)
    assert credenciais.para_visao() == conta
    assert reaberto.buscar_por_id("ausente") is None


def test_duplicidade_normalizada_nao_sobrescreve(repositorio):
    original = repositorio.salvar_secretario(dados("Sec-Téste"), senha_hash="hash-original")
    with pytest.raises(IdentificadorEmUso):
        repositorio.salvar_secretario(dados("  SEC-TÉSTE "), senha_hash="outro-hash")
    assert len(repositorio.listar_secretarios()) == 1
    assert repositorio.buscar_por_id(original.id).senha_hash == "hash-original"


def test_sql_parametrizado_preserva_texto_de_entrada(repositorio):
    identificador = "secretario'; drop table contas; --"
    conta = repositorio.salvar_secretario(dados(identificador), senha_hash="hash-sintetico")
    assert repositorio.buscar_por_identificador(identificador).id == conta.id
    assert repositorio.listar_secretarios() == [conta]


def test_administrador_inicial_unico_e_inicializacao_idempotente(repositorio):
    admin = repositorio.inicializar_administrador(dados("admin-ficticio"), senha_hash="hash-admin")
    assert admin.perfil is Perfil.ADMINISTRADOR
    with pytest.raises(ErroValidacao, match="já existe"):
        repositorio.inicializar_administrador(dados("outro-admin"), senha_hash="outro-hash")
    repositorio.inicializar()
    assert repositorio.buscar_por_id(admin.id).senha_hash == "hash-admin"
    assert repositorio.listar_secretarios() == []
    with pytest.raises(ContaNaoEncontrada):
        repositorio.atualizar_secretario(admin.id, {"nome": "Não permitido"})
    assert repositorio.buscar_por_id(admin.id).nome == admin.nome


def test_sessao_expira_na_fronteira_e_logout_revoga(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    criar_sessao(repositorio, conta)
    assert repositorio.buscar_sessao(token_hash(), 199).id == conta.id
    assert repositorio.buscar_sessao(token_hash(), 200) is None
    repositorio.revogar_sessao(token_hash())
    repositorio.revogar_sessao(token_hash())
    assert repositorio.buscar_sessao(token_hash(), 100) is None
    with sqlite3.connect(repositorio.caminho) as conexao:
        assert conexao.execute("SELECT count(*) FROM sessoes").fetchone()[0] == 0


@pytest.mark.parametrize("alteracoes,novo_hash", [
    ({"ativa": False}, None),
    ({}, "hash-novo"),
    ({"identificador": "identificador-novo"}, None),
])
def test_mudanca_de_acesso_revoga_todas_sessoes_da_conta(repositorio, alteracoes, novo_hash):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    outra = repositorio.salvar_secretario(dados("outro-secretario"), senha_hash="hash-sintetico")
    criar_sessao(repositorio, conta)
    criar_sessao(repositorio, conta, token="segundo-token")
    criar_sessao(repositorio, outra, token="outra-conta")
    repositorio.atualizar_secretario(conta.id, alteracoes, senha_hash=novo_hash)
    assert repositorio.buscar_sessao(token_hash(), 100) is None
    assert repositorio.buscar_sessao(token_hash("segundo-token"), 100) is None
    assert repositorio.buscar_sessao(token_hash("outra-conta"), 100).id == outra.id
    with sqlite3.connect(repositorio.caminho) as conexao:
        assert conexao.execute("SELECT count(*) FROM sessoes WHERE conta_id = ?", (conta.id,)).fetchone()[0] == 0


def test_renomear_preserva_sessoes(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    criar_sessao(repositorio, conta)
    atualizada = repositorio.atualizar_secretario(conta.id, {"nome": "Novo nome fictício"})
    assert atualizada.nome == "Novo nome fictício"
    assert repositorio.buscar_sessao(token_hash(), 100).nome == atualizada.nome


def test_erro_de_unicidade_desfaz_reset_e_preserva_sessao(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    repositorio.salvar_secretario(dados("ocupado"), senha_hash="hash-sintetico")
    criar_sessao(repositorio, conta)
    with pytest.raises(IdentificadorEmUso):
        repositorio.atualizar_secretario(conta.id, {"identificador": "OCUPADO"}, senha_hash="hash-novo")
    assert repositorio.buscar_por_id(conta.id).senha_hash == "hash-sintetico"
    assert repositorio.buscar_sessao(token_hash(), 100).id == conta.id


def test_falha_ao_revogar_desfaz_atualizacao_inteira(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    criar_sessao(repositorio, conta)
    with sqlite3.connect(repositorio.caminho) as conexao:
        conexao.execute("""CREATE TRIGGER falhar_revogacao BEFORE DELETE ON sessoes
            BEGIN SELECT RAISE(ABORT, 'falha sintetica'); END""")
    with pytest.raises(ErroPersistencia):
        repositorio.atualizar_secretario(conta.id, {"ativa": False}, senha_hash="hash-novo")
    credenciais = repositorio.buscar_por_id(conta.id)
    assert credenciais.ativa is True
    assert credenciais.senha_hash == "hash-sintetico"
    assert repositorio.buscar_sessao(token_hash(), 100).id == conta.id


def test_criar_sessao_nao_aceita_hash_anterior_ou_conta_desativada(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    repositorio.atualizar_secretario(conta.id, {}, senha_hash="hash-novo")
    with pytest.raises(FalhaAutenticacao):
        criar_sessao(repositorio, conta)
    criar_sessao(repositorio, conta, senha_hash="hash-novo")
    repositorio.atualizar_secretario(conta.id, {"ativa": False})
    with pytest.raises(FalhaAutenticacao):
        criar_sessao(repositorio, conta, senha_hash="hash-novo")
    with pytest.raises(FalhaAutenticacao):
        repositorio.criar_sessao("inexistente", token_hash(), 200, senha_hash_esperada="hash")


def test_banco_existente_desconhecido_nao_e_sobrescrito(tmp_path):
    caminho = tmp_path / "externo.sqlite3"
    with sqlite3.connect(caminho) as conexao:
        conexao.execute("CREATE TABLE externo (valor TEXT)")
        conexao.execute("INSERT INTO externo VALUES ('preservar')")
    with pytest.raises(ErroPersistencia):
        RepositorioContasSQLite(caminho).inicializar()
    with sqlite3.connect(caminho) as conexao:
        assert conexao.execute("SELECT valor FROM externo").fetchone()[0] == "preservar"
        assert conexao.execute("SELECT name FROM sqlite_master WHERE name = 'contas'").fetchone() is None


def test_falha_sql_nao_expoe_caminho(tmp_path):
    repo = RepositorioContasSQLite(tmp_path / "banco-privado.sqlite3")
    with pytest.raises(ErroPersistencia) as erro:
        repo.buscar_por_id("ausente")
    assert str(tmp_path) not in str(erro.value)
