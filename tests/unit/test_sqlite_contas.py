"""Persistência experimental de contas usando somente dados sintéticos em tmp_path."""

from dataclasses import FrozenInstanceError
import sqlite3

import pytest

from app.erros import (
    ContaNaoEncontrada,
    ErroPersistencia,
    ErroValidacao,
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


@pytest.mark.parametrize("alteracoes,novo_hash", [
    ({"ativa": False}, None), ({}, "hash-novo"), ({"identificador": "novo"}, None),
])
def test_alteracao_acesso_atualiza_versao_apenas_da_conta_alvo(repositorio, alteracoes, novo_hash):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    outra = repositorio.salvar_secretario(dados("outra"), senha_hash="hash-outra")
    atualizada = repositorio.atualizar_secretario(conta.id, alteracoes, senha_hash=novo_hash)
    assert atualizada.versao_sessao == conta.versao_sessao + 1
    assert repositorio.buscar_por_id(outra.id).versao_sessao == outra.versao_sessao


def test_renomear_preserva_versao(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-sintetico")
    atualizada = repositorio.atualizar_secretario(conta.id, {"nome": "Novo nome"})
    assert atualizada.nome == "Novo nome"
    assert atualizada.versao_sessao == conta.versao_sessao


def test_unicidade_desfaz_senha_situacao_e_versao_juntas(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-original")
    repositorio.salvar_secretario(dados("ocupado"), senha_hash="hash-outra")
    antes = repositorio.buscar_por_id(conta.id)
    with pytest.raises(IdentificadorEmUso):
        repositorio.atualizar_secretario(
            conta.id, {"identificador": "OCUPADO", "ativa": False}, senha_hash="hash-novo"
        )
    assert repositorio.buscar_por_id(conta.id) == antes


def test_falha_escrita_preserva_credenciais_e_versao(repositorio):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-original")
    antes = repositorio.buscar_por_id(conta.id)
    with sqlite3.connect(repositorio.caminho) as con:
        con.execute("""CREATE TRIGGER falhar BEFORE UPDATE ON contas
            BEGIN SELECT RAISE(ABORT, 'falha sintetica'); END""")
    with pytest.raises(ErroPersistencia):
        repositorio.atualizar_secretario(conta.id, {"ativa": False}, senha_hash="hash-novo")
    assert repositorio.buscar_por_id(conta.id) == antes


def test_migracao_v1_preserva_contas_e_remove_tabela_sessoes(tmp_path):
    caminho = tmp_path / "antigo.sqlite3"
    with sqlite3.connect(caminho) as con:
        con.execute("""CREATE TABLE contas (
            id TEXT PRIMARY KEY, perfil TEXT NOT NULL, nome TEXT NOT NULL,
            identificador TEXT NOT NULL UNIQUE, ativa INTEGER NOT NULL, senha_hash TEXT NOT NULL
        )""")
        con.execute("INSERT INTO contas VALUES ('id-antigo', 'ADMINISTRADOR', 'Admin antigo', 'admin.fixture', 1, 'hash-antigo')")
        con.execute("CREATE TABLE sessoes (token_hash TEXT, conta_id TEXT, expira_em INTEGER)")
        con.execute("INSERT INTO sessoes VALUES ('token-antigo', 'id-antigo', 999999)")
        con.execute("PRAGMA user_version = 1")
    repo = RepositorioContasSQLite(caminho)
    repo.inicializar()
    conta = repo.buscar_por_id("id-antigo")
    assert conta.nome == "Admin antigo"
    assert conta.senha_hash == "hash-antigo"
    assert conta.identificador == "admin.fixture"
    assert conta.versao_sessao == 0
    repo.inicializar()
    with sqlite3.connect(caminho) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 2
        assert con.execute("SELECT name FROM sqlite_master WHERE name='sessoes'").fetchone() is None


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
