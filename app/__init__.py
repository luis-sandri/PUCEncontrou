"""Fábrica da aplicação; ponto de composição mantido por Luís."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from flask import Flask

from app.config import carregar_configuracao


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Cria instância isolada; módulos de negócio exigem habilitação explícita."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(carregar_configuracao())
    if config is not None:
        app.config.from_mapping(config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Defina PUC_SECRET_KEY fora do Git antes de iniciar a aplicação.")

    from app.routes.publicas import bp
    from app.routes.documentacao import bp as documentacao_bp

    app.register_blueprint(bp)
    app.register_blueprint(documentacao_bp)

    if not isinstance(app.config["CONTAS_HABILITADAS"], bool):
        raise RuntimeError("CONTAS_HABILITADAS deve ser um booleano.")
    if not isinstance(app.config["OCORRENCIAS_HABILITADAS"], bool):
        raise RuntimeError("OCORRENCIAS_HABILITADAS deve ser um booleano.")
    if app.config["OCORRENCIAS_HABILITADAS"] and not app.config["CONTAS_HABILITADAS"]:
        raise RuntimeError("Habilite o módulo de contas para proteger as ações sobre ocorrências.")
    if app.config["CONTAS_HABILITADAS"]:
        from app.cli import contas_cli
        from app.repositories.json_contas import RepositorioContasJSON
        from app.routes.autenticacao import bp as autenticacao_bp
        from app.routes.contas import bp as contas_bp
        from app.services.autenticacao import ServicoAutenticacao
        from app.services.contas import ServicoContas

        duracao = app.config["CONTAS_DURACAO_SESSAO_SEGUNDOS"]
        if type(duracao) is not int or duracao <= 0:
            raise ValueError("A duração da sessão deve ser um inteiro positivo.")
        repositorio = RepositorioContasJSON(app.config["CONTAS_JSON"])
        app.extensions["autenticacao"] = ServicoAutenticacao(repositorio)
        app.extensions["contas"] = ServicoContas(repositorio)
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=duracao)
        app.config["SESSION_REFRESH_EACH_REQUEST"] = False
        app.register_blueprint(autenticacao_bp)
        app.register_blueprint(contas_bp)
        app.cli.add_command(contas_cli)

        if app.config["OCORRENCIAS_HABILITADAS"]:
            from app.composicao import compor_ocorrencias
            from app.routes.ocorrencias import bp as ocorrencias_bp
            from app.services.atendimento_ocorrencias import AtendimentoOcorrencias
            from app.repositories.fotos import FotosLocais

            for chave in ("SETOR_GUARDA_PUBLICO", "CANCELAMENTO_HABILITADO"):
                if type(app.config[chave]) is not bool:
                    raise ValueError(f"{chave} deve ser booleano.")
            fotos = FotosLocais(
                app.config["FOTOS_DIRETORIO"], limite_bytes=app.config["FOTOS_LIMITE_BYTES"],
                formatos=app.config["FOTOS_FORMATOS"],
            )
            dependencias = compor_ocorrencias(app.config)
            app.extensions["ocorrencias"] = AtendimentoOcorrencias(
                dependencias.nucleo, dependencias.consulta_periodo, repositorio, fotos,
                setor_publico=app.config["SETOR_GUARDA_PUBLICO"],
                cancelamento_habilitado=app.config["CANCELAMENTO_HABILITADO"],
            )
            app.register_blueprint(ocorrencias_bp)
    return app
