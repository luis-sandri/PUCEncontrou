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
    """Prepara o JSON de contas e cria somente o primeiro administrador."""
    nome = click.prompt("Nome")
    identificador = click.prompt("E-mail institucional (@pucpr.edu.br)")
    senha = click.prompt("Senha", hide_input=True, confirmation_prompt=True)
    try:
        current_app.extensions["autenticacao"].inicializar_administrador(
            {"nome": nome, "identificador": identificador}, senha
        )
    except ErroAplicacao as exc:
        mensagem = (
            "Não foi possível inicializar o arquivo de contas."
            if isinstance(exc, ErroPersistencia)
            else str(exc)
        )
        raise click.ClickException(mensagem) from None
    click.echo("Administrador inicial criado.")


@contas_cli.command("preparar-arquivo")
@with_appcontext
def preparar_arquivo():
    """Prepara um arquivo de contas vazio; valida o existente sem sobrescrever."""
    try:
        current_app.extensions["autenticacao"].preparar_arquivo()
    except ErroAplicacao:
        raise click.ClickException("Não foi possível preparar o arquivo de contas.") from None
    click.echo("Arquivo de contas preparado.")


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
        mensagem = "Arquivo de contas indisponível." if isinstance(exc, ErroPersistencia) else str(exc)
        raise click.ClickException(mensagem) from None
    click.echo("Acesso do administrador recuperado; faça login novamente.")


@contas_cli.command("importar-sqlite")
@click.argument("origem", type=click.Path(exists=True, dir_okay=False))
@with_appcontext
def importar_sqlite(origem):
    """Importa contas do protótipo anterior sem modificar a origem ou JSON existente."""
    try:
        quantidade = current_app.extensions["autenticacao"].importar_contas_legadas(origem)
    except ErroAplicacao as exc:
        mensagem = "Não foi possível importar o legado de contas." if isinstance(exc, ErroPersistencia) else str(exc)
        raise click.ClickException(mensagem) from None
    click.echo(f"{quantidade} conta(s) importada(s) para JSON.")
