"""Formulários mínimos de contas, preparados para integração visual com Mariana."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.erros import ErroValidacao, IdentificadorEmUso
from app.routes.seguranca import (
    configurar_blueprint, conta_publica, dados_formulario, exigir_autenticacao, gestao_contas,
)

bp = Blueprint("contas", __name__, url_prefix="/contas")
configurar_blueprint(bp)


def listar(erro=None, valores=None, status=200):
    contas = gestao_contas().listar_secretarios(ator=g.ator)
    return render_template(
        "contas/secretarios.html", contas=[conta_publica(conta) for conta in contas],
        erro=erro, valores=valores or {},
    ), status


def editar(conta_id, erro=None, valores=None, status=200):
    conta = gestao_contas().obter_secretario(conta_id, ator=g.ator)
    return render_template(
        "contas/editar_secretario.html", conta=conta_publica(conta),
        erro=erro, valores=valores if valores is not None else conta_publica(conta),
    ), status


def confirmar_senha(dados):
    if dados.get("senha") != dados.get("confirmacao_senha"):
        raise ErroValidacao("A confirmação da senha não confere.")


@bp.route("/secretarios", methods=["GET", "POST"])
@exigir_autenticacao
def listar_secretarios():
    if request.method == "POST":
        dados = dados_formulario({"nome", "identificador", "senha", "confirmacao_senha"})
        valores = {chave: dados.get(chave, "") for chave in ("nome", "identificador")}
        # Confirma a permissão antes de validar dados ou gerar hash.
        gestao_contas().listar_secretarios(ator=g.ator)
        try:
            confirmar_senha(dados)
            gestao_contas().cadastrar_secretario(valores, dados.get("senha"), ator=g.ator)
        except (ErroValidacao, IdentificadorEmUso) as exc:
            return listar(str(exc), valores, 409 if isinstance(exc, IdentificadorEmUso) else 400)
        flash("Secretário cadastrado.", "success")
        return redirect(url_for("contas.listar_secretarios"), code=303)
    return listar()


@bp.route("/secretarios/<conta_id>/editar", methods=["GET", "POST"])
@exigir_autenticacao
def editar_secretario(conta_id):
    if request.method == "POST":
        dados = dados_formulario({"nome", "identificador"})
        try:
            gestao_contas().gerenciar_secretario(conta_id, dados, ator=g.ator)
        except (ErroValidacao, IdentificadorEmUso) as exc:
            return editar(conta_id, str(exc), dados, 409 if isinstance(exc, IdentificadorEmUso) else 400)
        flash("Dados do secretário atualizados.", "success")
        return redirect(url_for("contas.listar_secretarios"), code=303)
    return editar(conta_id)


@bp.post("/secretarios/<conta_id>/situacao")
@exigir_autenticacao
def alterar_situacao(conta_id):
    dados = dados_formulario({"ativa"})
    if dados.get("ativa") not in {"true", "false"}:
        raise ErroValidacao("Situação de conta inválida.")
    ativa = dados["ativa"] == "true"
    gestao_contas().gerenciar_secretario(conta_id, {"ativa": ativa}, ator=g.ator)
    flash("Secretário reativado." if ativa else "Secretário desativado.", "success")
    return redirect(url_for("contas.listar_secretarios"), code=303)


@bp.post("/secretarios/<conta_id>/senha")
@exigir_autenticacao
def redefinir_senha(conta_id):
    dados = dados_formulario({"senha", "confirmacao_senha"})
    gestao_contas().obter_secretario(conta_id, ator=g.ator)
    try:
        confirmar_senha(dados)
        gestao_contas().gerenciar_secretario(conta_id, {"senha": dados.get("senha")}, ator=g.ator)
    except ErroValidacao as exc:
        return editar(conta_id, str(exc), status=400)
    flash("Senha redefinida. O secretário deverá entrar novamente.", "success")
    return redirect(url_for("contas.listar_secretarios"), code=303)
