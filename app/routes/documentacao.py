"""OpenAPI da superfície HTTP ativa, sem executar serviços de negócio."""

import re

from flask import Blueprint, current_app, jsonify, render_template

bp = Blueprint("documentacao", __name__)

# endpoint: resumo, perfil exigido, campos POST (None para endpoints sem POST).
OPERACOES = {
    "publicas.inicio": ("Página inicial", None, None),
    "autenticacao.login": ("Entrar com e-mail institucional e senha", None, "identificador senha"),
    "autenticacao.consultar_sessao": ("Consultar sessão atual", "AUTENTICADO", None),
    "autenticacao.logout": ("Sair da sessão", "AUTENTICADO", ""),
    "contas.listar_secretarios": ("Listar ou cadastrar secretários", "ADMINISTRADOR", "nome identificador senha confirmacao_senha"),
    "contas.editar_secretario": ("Consultar ou editar secretário", "ADMINISTRADOR", "nome identificador"),
    "contas.alterar_situacao": ("Ativar ou desativar secretário", "ADMINISTRADOR", "ativa"),
    "contas.redefinir_senha": ("Redefinir senha do secretário", "ADMINISTRADOR", "senha confirmacao_senha"),
    "ocorrencias.listar": ("Consultar ocorrências públicas", None, None),
    "ocorrencias.cadastrar": ("Abrir formulário ou cadastrar ocorrência", None, "tipo nome categoria data_ocorrencia local_ocorrencia descricao cor situacao_guarda setor_guarda foto"),
    "ocorrencias.detalhar": ("Consultar detalhes da ocorrência", None, None),
    "ocorrencias.foto": ("Consultar foto pública", None, None),
    "ocorrencias.editar": ("Abrir formulário ou editar ocorrência", "SECRETARIO", "nome categoria data_ocorrencia local_ocorrencia descricao cor situacao_guarda setor_guarda data_recebimento destinacao_a_verificar foto"),
    "ocorrencias.excluir": ("Excluir ocorrência com confirmação", "SECRETARIO", "confirmacao"),
    "ocorrencias.alterar_status": ("Resolver, reabrir ou cancelar ocorrência", "SECRETARIO", "novo_status confirmacao_presencial"),
    "ocorrencias.vincular": ("Vincular perdido e encontrado", "SECRETARIO", "perdido_id encontrado_id"),
}


def campo(nome):
    schema = {"type": "string"}
    if nome in {"senha", "confirmacao_senha"}:
        schema.update(format="password", minLength=12, maxLength=128)
    elif nome in {"data_ocorrencia", "data_recebimento", "inicio", "fim"}:
        schema["format"] = "date"
    elif nome == "foto":
        schema.update(format="binary", description=(
            f"JPEG/PNG válido, até {current_app.config['FOTOS_LIMITE_BYTES']} bytes. "
            "Obrigatório no cadastro; substituição opcional na edição."
        ))
    enums = {
        "tipo": ["PERDIDO", "ENCONTRADO"],
        "status": ["ABERTO", "RESOLVIDO", "CANCELADO"],
        "novo_status": (
            ["ABERTO", "RESOLVIDO", "CANCELADO"]
            if current_app.config["CANCELAMENTO_HABILITADO"]
            else ["ABERTO", "RESOLVIDO"]
        ),
        "ativa": ["true", "false"], "destinacao_a_verificar": ["true", "false"],
        "confirmacao": ["sim"], "confirmacao_presencial": ["sim"],
        "situacao_guarda": ["EM_SETOR", "AINDA_NAO_ENTREGUE"],
    }
    if nome in enums:
        schema["enum"] = enums[nome]
    if nome == "identificador":
        schema["description"] = "E-mail institucional @pucpr.edu.br."
    return schema


def operacao(endpoint, metodo):
    resumo, perfil, campos = OPERACOES[endpoint]
    resultado = {
        "operationId": f"{endpoint.replace('.', '_')}_{metodo}",
        "summary": resumo,
        "tags": [endpoint.split('.')[0]],
        "responses": {"200": {"description": "Página HTML.", "content": {
            "text/html": {"schema": {"type": "string"}}
        }}},
    }
    if perfil:
        resultado["security"] = [{"sessaoFlask": []}]
        resultado["description"] = f"Perfil: {perfil}. Sem sessão válida, redireciona para /login."
        resultado["responses"]["302"] = {"description": "Redirecionamento para login ou sessão existente."}
        resultado["responses"]["403"] = {"description": "Permissão insuficiente ou CSRF inválido (HTML)."}
    if endpoint != "publicas.inicio":
        for codigo, texto in {"400": "Entrada inválida", "404": "Registro não encontrado", "409": "Conflito", "503": "Persistência indisponível"}.items():
            resultado["responses"][codigo] = {"description": texto + " (HTML)."}
    if endpoint == "autenticacao.login":
        resultado["responses"]["302"] = {"description": "Já autenticado; redireciona para /sessao."}
    if metodo == "post":
        nomes = campos.split()
        propriedades = {nome: campo(nome) for nome in nomes}
        propriedades["csrf_token"] = {"type": "string", "description": "Copie o campo oculto de um formulário GET usando a mesma sessão. Após login, obtenha um novo token."}
        obrigatorios = ["csrf_token"]
        if endpoint == "ocorrencias.cadastrar":
            obrigatorios += ["tipo", "nome", "categoria", "data_ocorrencia", "local_ocorrencia", "foto"]
        elif endpoint == "ocorrencias.vincular":
            obrigatorios += nomes
        elif endpoint == "ocorrencias.alterar_status":
            obrigatorios += ["novo_status"]
        elif not endpoint.startswith("ocorrencias.") or endpoint == "ocorrencias.excluir":
            obrigatorios += nomes
        media = "multipart/form-data" if "foto" in nomes else "application/x-www-form-urlencoded"
        resultado["requestBody"] = {"required": True, "content": {media: {"schema": {
            "type": "object", "additionalProperties": False,
            "properties": propriedades, "required": obrigatorios,
        }}}}
        resultado["responses"]["303"] = {"description": "Operação concluída; redireciona para a página correspondente."}
        resultado["responses"]["403"] = {"description": "Permissão insuficiente ou CSRF inválido (HTML)."}
        resultado["responses"]["413"] = {"description": "Corpo excede o limite permitido (HTML)."}
        resultado["responses"]["415"] = {"description": "Tipo de conteúdo não aceito (HTML)."}
        if endpoint == "autenticacao.login":
            resultado["responses"]["401"] = {"description": "Credenciais inválidas (HTML)."}
    if endpoint == "ocorrencias.foto":
        resultado["responses"]["200"] = {"description": "Imagem validada.", "content": {
            mime: {"schema": {"type": "string", "format": "binary"}}
            for mime in ("image/jpeg", "image/png")
        }}
    if endpoint == "ocorrencias.listar":
        filtros = ["tipo", "status", "categoria", "local_ocorrencia"]
        if current_app.config["SETOR_GUARDA_PUBLICO"]:
            filtros += ["situacao_guarda", "setor_guarda"]
        filtros += ["q", "inicio", "fim"]
        resultado["parameters"] = [{"in": "query", "name": nome, "schema": campo(nome)} for nome in filtros]
    if endpoint == "ocorrencias.cadastrar" and metodo == "get":
        resultado["parameters"] = [{"in": "query", "name": "tipo", "schema": campo("tipo")}]
    if endpoint == "ocorrencias.alterar_status":
        resultado["description"] += (
            " Resolver exige confirmacao_presencial=sim e afeta o par vinculado. "
            "Reabrir também afeta o par. Cancelar exige ocorrência ABERTO sem vínculo, "
            "sem justificativa por enquanto; depende de CANCELAMENTO_HABILITADO."
        )
    return resultado


@bp.after_request
def impedir_cache(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.get("/openapi.json")
def especificacao():
    paths = {}
    for regra in current_app.url_map.iter_rules():
        if regra.endpoint not in OPERACOES:
            continue
        caminho = re.sub(r"<(?:(?:[^:>]+):)?([^>]+)>", r"{\1}", regra.rule)
        item = paths.setdefault(caminho, {})
        if regra.arguments:
            item["parameters"] = [{"in": "path", "name": nome, "required": True,
                                   "schema": {"type": "string"}} for nome in sorted(regra.arguments)]
        for metodo in sorted(regra.methods & {"GET", "POST"}):
            item[metodo.lower()] = operacao(regra.endpoint, metodo.lower())
    return jsonify({
        "openapi": "3.0.3",
        "info": {"title": "PUC Encontrou — HTTP", "version": "1.0.0", "description": (
            "Rotas ativas nesta instância. Respostas HTML e redirecionamentos; não é uma API JSON. "
            "POST usa formulários e csrf_token da mesma sessão. Faça login nos formulários da aplicação "
            "e copie um token atual para testar aqui. ADMINISTRADOR não herda poderes de SECRETARIO. "
            "Contas e ocorrências desabilitadas não aparecem nesta especificação."
        )},
        "paths": paths,
        "components": {"securitySchemes": {"sessaoFlask": {
            "type": "apiKey", "in": "cookie", "name": current_app.config["SESSION_COOKIE_NAME"],
            "description": "Cookie HttpOnly emitido pelo login. Use o login da aplicação na mesma origem; não cole o cookie em Authorize.",
        }}},
    })


@bp.get("/swagger")
def swagger():
    return render_template("swagger.html")
