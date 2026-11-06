"""Login e logout por formulários Jinja e sessão assinada do Flask."""

import time

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for

from app.erros import ErroValidacao, FalhaAutenticacao
from app.routes.seguranca import (
    autenticacao, configurar_blueprint, dados_formulario, exigir_autenticacao,
)

bp = Blueprint("autenticacao", __name__)
configurar_blueprint(bp)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        dados = dados_formulario({"identificador", "senha"})
        try:
            conta = autenticacao().autenticar(dados.get("identificador"), dados.get("senha"))
        except (FalhaAutenticacao, ErroValidacao) as exc:
            return render_template(
                "autenticacao/login.html", erro=str(exc),
                identificador=dados.get("identificador", ""),
            ), 401
        session.clear()
        session.permanent = True
        session["conta_id"] = conta.id
        session["versao_sessao"] = conta.versao_sessao
        session["expira_em"] = time.time() + current_app.config["CONTAS_DURACAO_SESSAO_SEGUNDOS"]
        return redirect(url_for("autenticacao.consultar_sessao"), code=303)
    if g.ator is not None:
        return redirect(url_for("autenticacao.consultar_sessao"))
    return render_template("autenticacao/login.html", identificador="")


@bp.get("/sessao")
@exigir_autenticacao
def consultar_sessao():
    return render_template("autenticacao/sessao.html")


@bp.post("/logout")
@exigir_autenticacao
def logout():
    dados_formulario(set())
    session.clear()
    return redirect(url_for("autenticacao.login"), code=303)
