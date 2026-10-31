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
    identificador = click.prompt("E-mail institucional (@pucpr.edu.br)")
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


@contas_cli.command("atualizar-banco")
@with_appcontext
def atualizar_banco():
    """Prepara/migra o banco, preservando contas; encerra sessões do protótipo v1."""
    try:
        current_app.extensions["autenticacao"].atualizar_banco()
    except ErroAplicacao:
        raise click.ClickException("Não foi possível atualizar o banco de contas.") from None
    click.echo("Banco de contas atualizado.")


@contas_cli.command("recuperar-administrador")
@with_appcontext
def recuperar_administrador():
    """Recupera o acesso ao administrador existente, somente por operação local."""
    click.confirm("Redefinir o acesso do administrador inicial?", abort=True)
    identificador = click.prompt("E-mail institucional (@pucpr.edu.br)")
    senha = click.prompt("Nova senha", hide_input=True, confirmation_prompt=True)
    try:
        current_app.extensions["autenticacao"].recuperar_administrador(identificador, senha)
    except ErroAplicacao as exc:
        mensagem = "Banco de contas indisponível." if isinstance(exc, ErroPersistencia) else str(exc)
        raise click.ClickException(mensagem) from None
    click.echo("Acesso do administrador recuperado; faça login novamente.")
