"""Configuração externa, sem acesso à persistência e sem segredos padrão."""

import os
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent


def _caminho_local(variavel: str, padrao: str) -> Path:
    caminho = Path(os.environ.get(variavel) or padrao)
    return caminho if caminho.is_absolute() else RAIZ_REPOSITORIO / caminho


def carregar_configuracao() -> dict[str, object]:
    """Lê o ambiente a cada fábrica, evitando estado global entre testes."""
    return {
        "SECRET_KEY": os.environ.get("PUC_SECRET_KEY"),
        "OCORRENCIAS_JSON": _caminho_local(
            "PUC_OCORRENCIAS_JSON", "instance/ocorrencias.json"
        ),
        "CONTAS_SQLITE": _caminho_local(
            "PUC_CONTAS_SQLITE", "instance/contas.sqlite3"
        ),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get(
            "PUC_SESSION_COOKIE_SECURE", "false"
        ).lower() == "true",
    }
