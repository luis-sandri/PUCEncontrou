"""Persistência experimental de contas usando somente dados sintéticos em tmp_path."""

from dataclasses import FrozenInstanceError
import json
import sqlite3

import pytest

from app.erros import (
    ContaNaoEncontrada,
    ErroPersistencia,
    ErroValidacao,
    IdentificadorEmUso,
)
from app.models.conta import Perfil
from app.repositories.json_contas import RepositorioContasJSON


@pytest.fixture
def repositorio(tmp_path):
    repo = RepositorioContasJSON(tmp_path / "contas.json")
    repo.inicializar()
    return repo


def dados(identificador="secretario-teste"):
    return {"nome": "Secretário fictício", "identificador": identificador}


def test_construtor_e_consulta_nao_criam_dados(tmp_path):
    caminho = tmp_path / "nao-criado" / "contas.json"
    repo = RepositorioContasJSON(caminho)
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
    reaberto = RepositorioContasJSON(repositorio.caminho)
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


def test_json_preserva_texto_literal_sem_interpretacao(repositorio):
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


def test_falha_escrita_preserva_arquivo_credenciais_e_versao(repositorio, monkeypatch):
    conta = repositorio.salvar_secretario(dados(), senha_hash="hash-original")
    antes = repositorio.buscar_por_id(conta.id)
    conteudo = repositorio.caminho.read_bytes()
    def falhar(*args):
        raise OSError("falha sintética")
    monkeypatch.setattr("app.repositories.json_contas.os.replace", falhar)
    with pytest.raises(ErroPersistencia):
        repositorio.atualizar_secretario(conta.id, {"ativa": False}, senha_hash="hash-novo")
    assert repositorio.buscar_por_id(conta.id) == antes
    assert repositorio.caminho.read_bytes() == conteudo
    assert list(repositorio.caminho.parent.glob(".contas-*.tmp")) == []


@pytest.mark.parametrize("conteudo", [b"{invalido", b"[]", b'{"versao":99,"contas":[]}', b'{"versao":1,"contas":"invalido"}'])
def test_arquivo_invalido_nunca_e_substituido_por_vazio(tmp_path, conteudo):
    caminho = tmp_path / "contas.json"
    caminho.write_bytes(conteudo)
    repo = RepositorioContasJSON(caminho)
    for operacao in (repo.inicializar, repo.listar_secretarios):
        with pytest.raises(ErroPersistencia):
            operacao()
        assert caminho.read_bytes() == conteudo


@pytest.mark.parametrize("alteracao", ["id_duplicado", "email_duplicado", "dois_admins", "ativa_texto", "senha_texto", "versao_negativa"])
def test_registros_invalidos_nao_sao_aceitos(repositorio, alteracao):
    repositorio.salvar_secretario(dados("um"), senha_hash="hash-um")
    repositorio.salvar_secretario(dados("dois"), senha_hash="hash-dois")
    documento = json.loads(repositorio.caminho.read_text())
    um, dois = documento["contas"]
    if alteracao == "id_duplicado":
        dois["id"] = um["id"]
    elif alteracao == "email_duplicado":
        dois["identificador"] = um["identificador"]
    elif alteracao == "dois_admins":
        um["perfil"] = dois["perfil"] = "ADMINISTRADOR"
    elif alteracao == "ativa_texto":
        um["ativa"] = "false"
    elif alteracao == "senha_texto":
        um["senha"] = "texto indevido"
    else:
        um["versao_sessao"] = -1
    repositorio.caminho.write_text(json.dumps(documento))
    antes = repositorio.caminho.read_bytes()
    with pytest.raises(ErroPersistencia):
        repositorio.salvar_secretario(dados("tres"), senha_hash="hash-tres")
    assert repositorio.caminho.read_bytes() == antes


def criar_legado(caminho, versao):
    with sqlite3.connect(caminho) as con:
        coluna = ", versao_sessao INTEGER NOT NULL DEFAULT 0" if versao == 2 else ""
        con.execute("CREATE TABLE contas (id TEXT PRIMARY KEY, perfil TEXT NOT NULL, nome TEXT NOT NULL, identificador TEXT NOT NULL UNIQUE, ativa INTEGER NOT NULL, senha_hash TEXT NOT NULL" + coluna + ")")
        con.execute("INSERT INTO contas (id,perfil,nome,identificador,ativa,senha_hash) VALUES ('id-antigo','ADMINISTRADOR','Admin antigo','admin.fixture',1,'hash-antigo')")
        con.execute(f"PRAGMA user_version = {versao}")


@pytest.mark.parametrize("versao", [1, 2])
def test_importacao_preserva_legado_e_contas(tmp_path, versao):
    origem = tmp_path / "antigo.sqlite3"
    criar_legado(origem, versao)
    antes = origem.read_bytes()
    repo = RepositorioContasJSON(tmp_path / "destino" / "contas.json")
    assert repo.importar_legado_sqlite(origem) == 1
    conta = repo.buscar_por_id("id-antigo")
    assert conta.nome == "Admin antigo"
    assert conta.senha_hash == "hash-antigo"
    assert conta.identificador == "admin.fixture"
    assert conta.versao_sessao == 0
    assert origem.read_bytes() == antes
    destino = repo.caminho.read_bytes()
    with pytest.raises(ErroValidacao, match="já existe"):
        repo.importar_legado_sqlite(origem)
    assert repo.caminho.read_bytes() == destino


def test_importacao_de_legado_invalido_nao_cria_destino(tmp_path):
    origem = tmp_path / "invalido.sqlite3"
    origem.write_bytes(b"nao e sqlite")
    repo = RepositorioContasJSON(tmp_path / "destino" / "contas.json")
    with pytest.raises(ErroPersistencia):
        repo.importar_legado_sqlite(origem)
    assert not repo.caminho.parent.exists()
    assert origem.read_bytes() == b"nao e sqlite"


def test_falha_de_leitura_nao_expoe_caminho(tmp_path):
    repo = RepositorioContasJSON(tmp_path / "privado" / "contas.json")
    with pytest.raises(ErroPersistencia) as erro:
        repo.buscar_por_id("ausente")
    assert str(tmp_path) not in str(erro.value)


def test_escritas_concorrentes_da_mesma_instancia_preservam_contas(repositorio):
    from concurrent.futures import ThreadPoolExecutor

    def inserir(numero):
        return repositorio.salvar_secretario(dados(f"secretario-{numero}"), senha_hash="hash-ficticio")

    with ThreadPoolExecutor(max_workers=4) as executor:
        criadas = list(executor.map(inserir, range(12)))
    assert {conta.id for conta in repositorio.listar_secretarios()} == {conta.id for conta in criadas}
