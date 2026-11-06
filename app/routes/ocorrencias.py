"""HTTP de Luís: formulários e projeções, sem acesso às estruturas ou arquivos."""

from functools import wraps
from io import BytesIO

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, send_file, url_for

from app.erros import ErroValidacao
from app.models.conta import Perfil
from app.models.ocorrencia import StatusOcorrencia
from app.routes.seguranca import configurar_blueprint, dados_formulario, exigir_autenticacao
from app.services.atendimento_ocorrencias import CAMPOS_GUARDA, CAMPOS_INTERNOS, CAMPOS_OBJETO, FILTROS

bp = Blueprint("ocorrencias", __name__, url_prefix="/ocorrencias")
configurar_blueprint(bp, limite_corpo=lambda: current_app.config["FOTOS_LIMITE_BYTES"] + 64 * 1024)


def atendimento():
    return current_app.extensions["ocorrencias"]


def exigir_secretario(funcao):
    @wraps(funcao)
    @exigir_autenticacao
    def protegida(*args, **kwargs):
        atendimento().exigir_secretario(g.ator)
        return funcao(*args, **kwargs)
    return protegida


def _foto():
    arquivo = request.files.get("foto")
    return arquivo.stream if arquivo is not None and arquivo.filename else None


def _formulario(valores=None, *, item=None, erro=None, status=200):
    valores = valores or {}
    return render_template(
        "ocorrencias/formulario.html", valores=valores, item=item, erro=erro,
        tipo=valores.get("tipo", item["tipo"] if item else "PERDIDO"),
        limite_foto=current_app.config["FOTOS_LIMITE_BYTES"],
        formatos_foto=current_app.config["FOTOS_FORMATOS"],
    ), status


@bp.get("")
def listar():
    permitidos = FILTROS | {"q", "inicio", "fim"}
    if set(request.args) - permitidos or any(len(request.args.getlist(c)) != 1 for c in request.args):
        raise ErroValidacao("Filtro desconhecido ou repetido.")
    filtros = {campo: request.args[campo] for campo in permitidos if campo in request.args}
    itens = atendimento().listar(filtros)
    return render_template("ocorrencias/lista.html", itens=[atendimento().visao(item) for item in itens], filtros=filtros,
                           setor_publico=atendimento().setor_publico)


@bp.route("/nova", methods=["GET", "POST"])
def cadastrar():
    if request.method == "POST":
        dados = dados_formulario(CAMPOS_OBJETO | CAMPOS_GUARDA | {"tipo"}, arquivos={"foto"})
        try:
            item = atendimento().cadastrar(dados, foto=_foto())
        except ErroValidacao as exc:
            return _formulario(dados, erro=str(exc), status=400)
        flash("Ocorrência cadastrada.", "success")
        return redirect(url_for("ocorrencias.detalhar", ocorrencia_id=item.id), code=303)
    tipo = request.args.get("tipo", "PERDIDO")
    if tipo not in {"PERDIDO", "ENCONTRADO"}:
        raise ErroValidacao("Tipo de ocorrência inválido.")
    return _formulario({"tipo": tipo})


@bp.get("/<ocorrencia_id>")
def detalhar(ocorrencia_id):
    servico = atendimento()
    item = servico.obter(ocorrencia_id)
    secretario = g.ator is not None and g.ator.perfil is Perfil.SECRETARIO
    visao = servico.visao(item, ator=g.ator, interna=secretario)
    opcoes = []
    if secretario and visao["status"] == "ABERTO" and not visao.get("vinculo_id"):
        oposto = "ENCONTRADO" if visao["tipo"] == "PERDIDO" else "PERDIDO"
        for candidato in servico.listar({"tipo": oposto, "status": "ABERTO"}):
            opcao = servico.visao(candidato, ator=g.ator, interna=True)
            if not opcao["vinculo_id"]:
                opcoes.append(opcao)
    return render_template(
        "ocorrencias/detalhe.html", item=visao, secretario=secretario, opcoes_vinculo=opcoes,
        cancelamento_habilitado=servico.cancelamento_habilitado,
    )


@bp.get("/<ocorrencia_id>/foto")
def foto(ocorrencia_id):
    imagem = atendimento().foto_publica(ocorrencia_id)
    return send_file(BytesIO(imagem.conteudo), mimetype=imagem.tipo_mime, download_name="foto")


@bp.route("/<ocorrencia_id>/editar", methods=["GET", "POST"])
@exigir_secretario
def editar(ocorrencia_id):
    servico = atendimento()
    item = servico.visao(servico.obter(ocorrencia_id), ator=g.ator, interna=True)
    if request.method == "POST":
        dados = dados_formulario(CAMPOS_OBJETO | CAMPOS_GUARDA | CAMPOS_INTERNOS, arquivos={"foto"})
        if "destinacao_a_verificar" in dados:
            if dados["destinacao_a_verificar"] not in {"true", "false"}:
                raise ErroValidacao("Destinação inválida.")
            dados["destinacao_a_verificar"] = dados["destinacao_a_verificar"] == "true"
        try:
            servico.editar(ocorrencia_id, dados, ator=g.ator, foto=_foto())
        except ErroValidacao as exc:
            return _formulario(dados, item=item, erro=str(exc), status=400)
        flash("Ocorrência atualizada.", "success")
        return redirect(url_for("ocorrencias.detalhar", ocorrencia_id=ocorrencia_id), code=303)
    return _formulario(item, item=item)


@bp.post("/<ocorrencia_id>/excluir")
@exigir_secretario
def excluir(ocorrencia_id):
    dados = dados_formulario({"confirmacao"})
    atendimento().excluir(ocorrencia_id, ator=g.ator, confirmacao=dados.get("confirmacao") == "sim")
    flash("Ocorrência excluída.", "success")
    return redirect(url_for("ocorrencias.listar"), code=303)


@bp.post("/<ocorrencia_id>/status")
@exigir_secretario
def alterar_status(ocorrencia_id):
    dados = dados_formulario({"novo_status", "confirmacao_presencial"})
    try:
        novo_status = StatusOcorrencia(dados.get("novo_status"))
    except (ValueError, TypeError):
        raise ErroValidacao("Status inválido.") from None
    atendimento().alterar_status(
        ocorrencia_id, novo_status, ator=g.ator,
        contexto={"confirmacao_presencial": dados.get("confirmacao_presencial") == "sim"},
    )
    flash("Situação atualizada, incluindo o par vinculado quando aplicável.", "success")
    return redirect(url_for("ocorrencias.detalhar", ocorrencia_id=ocorrencia_id), code=303)


@bp.post("/vinculos")
@exigir_secretario
def vincular():
    dados = dados_formulario({"perdido_id", "encontrado_id"})
    if not dados.get("perdido_id") or not dados.get("encontrado_id"):
        raise ErroValidacao("Informe as duas ocorrências do vínculo.")
    atendimento().vincular(dados["perdido_id"], dados["encontrado_id"], ator=g.ator)
    flash("Ocorrências vinculadas. A devolução ainda precisa de confirmação presencial.", "success")
    return redirect(url_for("ocorrencias.detalhar", ocorrencia_id=dados["perdido_id"]), code=303)
