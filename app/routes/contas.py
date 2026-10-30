"""API administrativa experimental, sem renderizar telas de Mariana."""

from flask import Blueprint, g, jsonify

from app.routes.seguranca import (
    configurar_blueprint,
    conta_publica,
    exigir_autenticacao,
    gestao_contas,
    objeto_json,
    verificar_csrf,
)

bp = Blueprint("contas", __name__, url_prefix="/contas")
configurar_blueprint(bp)


@bp.get("/secretarios")
@exigir_autenticacao
def listar_secretarios():
    contas = gestao_contas().listar_secretarios(ator=g.ator)
    return jsonify(contas=[conta_publica(conta) for conta in contas])


@bp.post("/secretarios")
@exigir_autenticacao
def cadastrar_secretario():
    verificar_csrf()
    dados = objeto_json(campos={"nome", "identificador", "senha"})
    senha = dados.pop("senha", None)
    conta = gestao_contas().cadastrar_secretario(dados, senha, ator=g.ator)
    return jsonify(conta=conta_publica(conta)), 201


@bp.patch("/secretarios/<conta_id>")
@exigir_autenticacao
def gerenciar_secretario(conta_id):
    verificar_csrf()
    alteracoes = objeto_json(campos={"nome", "identificador", "ativa", "senha"})
    conta = gestao_contas().gerenciar_secretario(conta_id, alteracoes, ator=g.ator)
    return jsonify(conta=conta_publica(conta))
