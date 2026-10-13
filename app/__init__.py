"""Fábrica da aplicação; ponto de composição mantido por Luís."""

from collections.abc import Mapping
from typing import Any

from flask import Flask

from app.config import carregar_configuracao


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Cria uma instância isolada, ainda sem serviços de negócio."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(carregar_configuracao())
    if config is not None:
        app.config.from_mapping(config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Defina PUC_SECRET_KEY fora do Git antes de iniciar a aplicação.")

    from app.routes.publicas import bp

    app.register_blueprint(bp)
    return app
