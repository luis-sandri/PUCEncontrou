"""Sessão do Flask, proteção dos formulários e tradução de erros para HTML."""

from functools import wraps
from hmac import compare_digest
import secrets
import time

from flask import current_app, g, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

from app.erros import (
    ContaNaoEncontrada, ErroPersistencia, ErroValidacao, FalhaAutenticacao,
    IdentificadorEmUso, PermissaoNegada,
)


def autenticacao():
    return current_app.extensions["autenticacao"]


def gestao_contas():
    return current_app.extensions["contas"]


def conta_publica(conta):
    """Somente os dados necessários às telas, sem hash ou versão interna."""
    return {
        "id": conta.id, "perfil": conta.perfil.value, "nome": conta.nome,
        "identificador": conta.identificador, "ativa": conta.ativa,
    }


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def verificar_csrf():
    esperado = session.get("csrf_token")
    recebido = request.form.get("csrf_token", "")
    if (
        not isinstance(esperado, str) or not recebido.isascii()
        or len(request.form.getlist("csrf_token")) != 1
        or not compare_digest(esperado, recebido)
    ):
        raise PermissaoNegada("Formulário expirado ou inválido. Recarregue a página.")


def dados_formulario(campos):
    if request.mimetype not in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        raise UnsupportedMediaType()
    verificar_csrf()
    if request.files or set(request.form) - (set(campos) | {"csrf_token"}):
        raise ErroValidacao("Campo não permitido.")
    if any(len(request.form.getlist(campo)) != 1 for campo in request.form):
        raise ErroValidacao("Campo repetido no formulário.")
    return {campo: request.form[campo] for campo in campos if campo in request.form}


def exigir_autenticacao(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if g.ator is None:
            return redirect(url_for("autenticacao.login"))
        return funcao(*args, **kwargs)
    return protegida


def configurar_blueprint(bp):
    @bp.before_request
    def carregar_ator():
        request.max_content_length = 16 * 1024
        g.ator = None
        conta_id = session.get("conta_id")
        if conta_id is not None:
            expira_em = session.get("expira_em")
            if isinstance(expira_em, (int, float)) and time.time() < expira_em:
                g.ator = autenticacao().obter_sessao(conta_id, session.get("versao_sessao"))
            if g.ator is None:
                session.clear()

    @bp.context_processor
    def contexto():
        return {
            "csrf_token": csrf_token,
            "ator_atual": conta_publica(g.ator) if g.ator else None,
        }

    @bp.after_request
    def impedir_cache(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    for erro, status in (
        (ErroValidacao, 400), (FalhaAutenticacao, 401), (PermissaoNegada, 403),
        (ContaNaoEncontrada, 404), (IdentificadorEmUso, 409), (ErroPersistencia, 503),
    ):
        def tratar(exc, codigo=status):
            mensagem = "Serviço de contas indisponível." if isinstance(exc, ErroPersistencia) else str(exc)
            return render_template("contas/erro.html", mensagem=mensagem), codigo
        bp.register_error_handler(erro, tratar)

    @bp.errorhandler(HTTPException)
    def tratar_http(exc):
        return render_template("contas/erro.html", mensagem=exc.name), exc.code
