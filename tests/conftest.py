"""Fixtures isoladas, sem uso de contas ou dados reais."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "chave-exclusiva-de-teste-sem-uso-real",
            "CONTAS_HABILITADAS": False,
            "OCORRENCIAS_JSON": tmp_path / "ocorrencias.json",
            "CONTAS_SQLITE": tmp_path / "contas.sqlite3",
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()
