"""API de autenticação experimental; registrada somente por opt-in."""

from flask import Blueprint, g, jsonify, session

from app.routes.seguranca import (
    autenticacao,
    configurar_blueprint,
    conta_publica,
    csrf_token,
    exigir_autenticacao,
    objeto_json,
    verificar_csrf,
)

bp = Blueprint("autenticacao", __name__)
configurar_blueprint(bp)


@bp.get("/login")
def preparar_login():
    return jsonify(csrf_token=csrf_token())


@bp.post("/login")
def login():
    verificar_csrf()
    dados = objeto_json(campos={"identificador", "senha"})
    conta, token = autenticacao().iniciar_sessao(
        dados.get("identificador"), dados.get("senha")
    )
    anterior = session.get("conta_token")
    if anterior:
        autenticacao().encerrar_sessao(anterior)
    session.clear()
    session.permanent = True
    session["conta_token"] = token
    return jsonify(conta=conta_publica(conta), csrf_token=csrf_token())


@bp.get("/sessao")
@exigir_autenticacao
def consultar_sessao():
    return jsonify(conta=conta_publica(g.ator), csrf_token=csrf_token())


@bp.post("/logout")
@exigir_autenticacao
def logout():
    verificar_csrf()
    autenticacao().encerrar_sessao(session["conta_token"])
    session.clear()
    return "", 204
