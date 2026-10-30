"""Provisionamento local explícito, sem credenciais padrão ou em argumentos."""

import click
from flask import current_app
from flask.cli import with_appcontext

from app.erros import ErroAplicacao, ErroPersistencia


@click.group("contas")
def contas_cli():
    """Administração local do módulo experimental de contas."""


@contas_cli.command("inicializar")
@with_appcontext
def inicializar():
    """Prepara o SQLite e cria somente o primeiro administrador."""
    nome = click.prompt("Nome")
    identificador = click.prompt("Identificador")
    senha = click.prompt("Senha", hide_input=True, confirmation_prompt=True)
    try:
        current_app.extensions["autenticacao"].inicializar_administrador(
            {"nome": nome, "identificador": identificador}, senha
        )
    except ErroAplicacao as exc:
        mensagem = (
            "Não foi possível inicializar o banco de contas."
            if isinstance(exc, ErroPersistencia)
            else str(exc)
        )
        raise click.ClickException(mensagem) from None
    click.echo("Administrador inicial criado.")
