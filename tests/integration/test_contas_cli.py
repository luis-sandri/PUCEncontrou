"""Bootstrap local de administrador sem senha em argumentos ou saída."""

import pytest

from app import create_app


pytestmark = pytest.mark.integracao

SENHA = "Senha-ficticia-exclusiva-123!"


@pytest.fixture
def app_cli(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "chave-isolada-dos-testes-da-cli",
            "CONTAS_HABILITADAS": True,
            "CONTAS_JSON": tmp_path / "dados" / "contas.json",
            "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json",
        }
    )


def _inicializar(app, nome="Administrador de teste", identificador="admin@pucpr.edu.br"):
    return app.test_cli_runner().invoke(
        args=["contas", "inicializar"],
        input=f"{nome}\n{identificador}\n{SENHA}\n{SENHA}\n",
    )


def test_bootstrap_e_explicito_pede_confirmacao_e_oculta_senha(app_cli):
    assert not app_cli.config["CONTAS_JSON"].exists()
    resultado = _inicializar(app_cli)
    assert resultado.exit_code == 0, resultado.output
    assert SENHA not in resultado.output
    assert app_cli.config["CONTAS_JSON"].exists()
    assert not app_cli.config["OCORRENCIAS_JSON"].exists()
    conta = app_cli.extensions["autenticacao"].autenticar("admin@pucpr.edu.br", SENHA)
    assert conta.perfil.value == "ADMINISTRADOR"
    assert not hasattr(conta, "senha_hash")


def test_repetir_bootstrap_nao_cria_novo_admin_nem_substitui_existente(app_cli):
    assert _inicializar(app_cli).exit_code == 0
    resultado = _inicializar(app_cli, "Outro administrador", "outro@pucpr.edu.br")
    assert resultado.exit_code != 0
    assert SENHA not in resultado.output
    original = app_cli.extensions["autenticacao"].autenticar("admin@pucpr.edu.br", SENHA)
    assert original.nome == "Administrador de teste"
    from app.erros import FalhaAutenticacao

    with pytest.raises(FalhaAutenticacao):
        app_cli.extensions["autenticacao"].autenticar("outro@pucpr.edu.br", SENHA)


def test_bootstrap_nao_aceita_senha_por_opcao(app_cli):
    resultado = app_cli.test_cli_runner().invoke(
        args=["contas", "inicializar", "--senha", SENHA]
    )
    assert resultado.exit_code != 0
    assert not app_cli.config["CONTAS_JSON"].exists()


def test_senhas_sem_confirmacao_igual_nao_criam_administrador(app_cli):
    resultado = app_cli.test_cli_runner().invoke(
        args=["contas", "inicializar"],
        input=f"Administrador de teste\nadmin@pucpr.edu.br\n{SENHA}\nSenha-diferente-123!\n",
    )
    assert resultado.exit_code != 0
    assert SENHA not in resultado.output
    # O comando não deve chegar ao serviço enquanto a confirmação falhar.
    assert not app_cli.config["CONTAS_JSON"].exists()


def test_recuperacao_local_exige_confirmacao_e_preserva_identidade(app_cli):
    assert _inicializar(app_cli).exit_code == 0
    auth = app_cli.extensions["autenticacao"]
    original = auth.autenticar("admin@pucpr.edu.br", SENHA)
    runner = app_cli.test_cli_runner()
    assert runner.invoke(args=["contas", "recuperar-administrador"], input="n\n").exit_code != 0
    nova = "Nova-senha-ficticia-5678!"
    resultado = runner.invoke(
        args=["contas", "recuperar-administrador"],
        input=f"y\nrecuperado@pucpr.edu.br\n{nova}\n{nova}\n",
    )
    assert resultado.exit_code == 0, resultado.output
    assert nova not in resultado.output
    recuperado = auth.autenticar("recuperado@pucpr.edu.br", nova)
    assert recuperado.id == original.id
    assert auth.obter_sessao(original.id, original.versao_sessao) is None


def test_preparar_arquivo_nao_cria_administrador(app_cli):
    resultado = app_cli.test_cli_runner().invoke(args=["contas", "preparar-arquivo"])
    assert resultado.exit_code == 0, resultado.output
    from app.erros import FalhaAutenticacao
    with pytest.raises(FalhaAutenticacao):
        app_cli.extensions["autenticacao"].autenticar("admin@pucpr.edu.br", SENHA)


def test_importacao_cli_preserva_hash_e_permite_login(app_cli, tmp_path):
    import sqlite3
    from werkzeug.security import generate_password_hash

    origem = tmp_path / "legado.sqlite3"
    senha_hash = generate_password_hash(SENHA)
    with sqlite3.connect(origem) as con:
        con.execute("""CREATE TABLE contas (
            id TEXT, perfil TEXT, nome TEXT, identificador TEXT,
            ativa INTEGER, senha_hash TEXT, versao_sessao INTEGER
        )""")
        con.execute(
            "INSERT INTO contas VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("admin-legado", "ADMINISTRADOR", "Admin fictício", "admin@pucpr.edu.br", 1, senha_hash, 3),
        )
        con.execute("PRAGMA user_version = 2")
    antes = origem.read_bytes()
    runner = app_cli.test_cli_runner()
    resultado = runner.invoke(args=["contas", "importar-sqlite", str(origem)])
    assert resultado.exit_code == 0, resultado.output
    assert SENHA not in resultado.output
    assert senha_hash not in resultado.output
    conta = app_cli.extensions["autenticacao"].autenticar("admin@pucpr.edu.br", SENHA)
    assert conta.id == "admin-legado"
    assert conta.versao_sessao == 3
    assert origem.read_bytes() == antes
    destino = app_cli.config["CONTAS_JSON"].read_bytes()
    assert runner.invoke(args=["contas", "importar-sqlite", str(origem)]).exit_code != 0
    assert app_cli.config["CONTAS_JSON"].read_bytes() == destino
