"""Fronteira HTTP do módulo experimental de contas, sem acesso ao SQLite."""

from functools import wraps
from hmac import compare_digest
import secrets

from flask import current_app, g, jsonify, request, session
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

from app.erros import (
    ContaNaoEncontrada,
    ErroPersistencia,
    ErroValidacao,
    FalhaAutenticacao,
    IdentificadorEmUso,
    PermissaoNegada,
)


def autenticacao():
    return current_app.extensions["autenticacao"]


def gestao_contas():
    return current_app.extensions["contas"]


def conta_publica(conta):
    """Projeção explícita: nunca serializar credenciais ou o modelo integral."""
    return {
        "id": conta.id,
        "perfil": conta.perfil.value,
        "nome": conta.nome,
        "identificador": conta.identificador,
        "ativa": conta.ativa,
    }


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def verificar_csrf():
    recebido = request.headers.get("X-CSRF-Token", "")
    esperado = session.get("csrf_token")
    if (
        not isinstance(esperado, str)
        or not recebido.isascii()
        or not compare_digest(esperado, recebido)
    ):
        raise PermissaoNegada("Token CSRF inválido. Recarregue a sessão.")


def objeto_json(*, campos=None):
    if not request.is_json:
        raise UnsupportedMediaType()
    dados = request.get_json()
    if not isinstance(dados, dict):
        raise ErroValidacao("Envie um objeto JSON.")
    if campos is not None and set(dados) - set(campos):
        raise ErroValidacao("Campo não permitido.")
    return dados


def exigir_autenticacao(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if g.ator is None:
            raise FalhaAutenticacao("Autenticação necessária.")
        return funcao(*args, **kwargs)

    return protegida


def configurar_blueprint(bp):
    @bp.before_request
    def carregar_ator():
        request.max_content_length = 16 * 1024
        g.ator = None
        token = session.get("conta_token")
        if token is not None:
            g.ator = autenticacao().obter_sessao(token)
            if g.ator is None:
                session.clear()

    @bp.after_request
    def impedir_cache(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    for erro, status in (
        (ErroValidacao, 400),
        (FalhaAutenticacao, 401),
        (PermissaoNegada, 403),
        (ContaNaoEncontrada, 404),
        (IdentificadorEmUso, 409),
        (ErroPersistencia, 503),
    ):
        def tratar(exc, codigo=status):
            # Não registrar exceção SQL, payload, caminho ou credenciais.
            mensagem = (
                "Serviço de contas indisponível."
                if isinstance(exc, ErroPersistencia)
                else str(exc)
            )
            return jsonify(erro=mensagem), codigo

        bp.register_error_handler(erro, tratar)

    @bp.errorhandler(HTTPException)
    def tratar_http(exc):
        return jsonify(erro=exc.name), exc.code
