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
            "CONTAS_SQLITE": tmp_path / "dados" / "contas.sqlite3",
            "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json",
        }
    )


def _inicializar(app, nome="Administrador de teste", identificador="admin.fixture"):
    return app.test_cli_runner().invoke(
        args=["contas", "inicializar"],
        input=f"{nome}\n{identificador}\n{SENHA}\n{SENHA}\n",
    )


def test_bootstrap_e_explicito_pede_confirmacao_e_oculta_senha(app_cli):
    assert not app_cli.config["CONTAS_SQLITE"].exists()
    resultado = _inicializar(app_cli)
    assert resultado.exit_code == 0, resultado.output
    assert SENHA not in resultado.output
    assert app_cli.config["CONTAS_SQLITE"].exists()
    assert not app_cli.config["OCORRENCIAS_JSON"].exists()
    conta = app_cli.extensions["autenticacao"].autenticar("admin.fixture", SENHA)
    assert conta.perfil.value == "ADMINISTRADOR"
    assert not hasattr(conta, "senha_hash")


def test_repetir_bootstrap_nao_cria_novo_admin_nem_substitui_existente(app_cli):
    assert _inicializar(app_cli).exit_code == 0
    resultado = _inicializar(app_cli, "Outro administrador", "outro.fixture")
    assert resultado.exit_code != 0
    assert SENHA not in resultado.output
    original = app_cli.extensions["autenticacao"].autenticar("admin.fixture", SENHA)
    assert original.nome == "Administrador de teste"
    from app.erros import FalhaAutenticacao

    with pytest.raises(FalhaAutenticacao):
        app_cli.extensions["autenticacao"].autenticar("outro.fixture", SENHA)


def test_bootstrap_nao_aceita_senha_por_opcao(app_cli):
    resultado = app_cli.test_cli_runner().invoke(
        args=["contas", "inicializar", "--senha", SENHA]
    )
    assert resultado.exit_code != 0
    assert not app_cli.config["CONTAS_SQLITE"].exists()


def test_senhas_sem_confirmacao_igual_nao_criam_administrador(app_cli):
    resultado = app_cli.test_cli_runner().invoke(
        args=["contas", "inicializar"],
        input=f"Administrador de teste\nadmin.fixture\n{SENHA}\nSenha-diferente-123!\n",
    )
    assert resultado.exit_code != 0
    assert SENHA not in resultado.output
    # O comando não deve chegar ao serviço enquanto a confirmação falhar.
    assert not app_cli.config["CONTAS_SQLITE"].exists()
