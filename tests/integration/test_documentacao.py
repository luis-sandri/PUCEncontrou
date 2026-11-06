"""Documentação acompanha a superfície habilitada sem abrir módulos de negócio."""

import re

import pytest

from app import create_app
from app.composicao import DependenciasOcorrencias
from tests.fakes_ocorrencias import ConsultaFake, criar_nucleo

pytestmark = pytest.mark.integracao


def test_swagger_e_especificacao_na_base(client, app):
    html = client.get('/swagger')
    assert html.status_code == 200
    assert html.headers['Cache-Control'] == 'no-store'
    assert 'SwaggerUIBundle' in html.text
    assert '/openapi.json' in html.text
    resposta = client.get('/openapi.json')
    assert resposta.mimetype == 'application/json'
    assert resposta.headers['Cache-Control'] == 'no-store'
    spec = resposta.json
    assert spec['openapi'] == '3.0.3'
    assert set(spec['paths']) == {'/'}
    assert client.get('/login').status_code == 404
    assert client.get('/ocorrencias').status_code == 404
    assert not app.config['CONTAS_JSON'].exists()


def test_documentacao_cobre_rotas_ativas_e_formularios(tmp_path):
    nucleo = criar_nucleo()
    app = create_app({
        'TESTING': True, 'SECRET_KEY': 'chave-ficticia-documentacao',
        'CONTAS_HABILITADAS': True, 'OCORRENCIAS_HABILITADAS': True,
        'CONTAS_JSON': tmp_path / 'contas.json',
        'FOTOS_DIRETORIO': tmp_path / 'fotos',
        'OCORRENCIAS_COMPOSITOR': lambda config: DependenciasOcorrencias(nucleo, ConsultaFake(nucleo)),
    })
    client = app.test_client()
    spec = client.get('/openapi.json').json
    esperadas = set()
    ids = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static' or rule.endpoint.startswith('documentacao.'):
            continue
        path = re.sub(r'<([^>]+)>', r'{\1}', rule.rule)
        for method in rule.methods & {'GET', 'POST'}:
            esperadas.add((path, method.lower()))
    documentadas = set()
    for path, item in spec['paths'].items():
        for method, op in item.items():
            if method == 'parameters':
                continue
            documentadas.add((path, method))
            ids.append(op['operationId'])
            if method == 'post':
                content = op['requestBody']['content']
                schema = next(iter(content.values()))['schema']
                assert 'csrf_token' in schema['required']
                assert schema['additionalProperties'] is False
    assert documentadas == esperadas
    assert len(ids) == len(set(ids))
    cadastro = spec['paths']['/ocorrencias/nova']['post']
    schema = cadastro['requestBody']['content']['multipart/form-data']['schema']
    assert 'foto' in schema['required']
    assert schema['properties']['foto']['format'] == 'binary'
    assert spec['paths']['/contas/secretarios']['post']['security'] == [{'sessaoFlask': []}]
    assert 'security' not in cadastro
    assert not (tmp_path / 'contas.json').exists()
    assert not (tmp_path / 'fotos').exists()
    # Consultar Swagger não cria sessão/token nem contorna o CSRF dos formulários.
    assert client.post('/login', data={'identificador': 'teste@pucpr.edu.br', 'senha': 'x'}).status_code == 403


def test_especificacao_isolada_com_contas_habilitadas(tmp_path, client):
    app = create_app({
        'SECRET_KEY': 'chave-ficticia', 'CONTAS_HABILITADAS': True,
        'OCORRENCIAS_HABILITADAS': False, 'CONTAS_JSON': tmp_path / 'contas.json',
    })
    paths = app.test_client().get('/openapi.json').json['paths']
    assert '/login' in paths
    assert '/ocorrencias' not in paths
    assert set(client.get('/openapi.json').json['paths']) == {'/'}


def test_especificacao_reflete_opcoes_de_guarda_e_cancelamento(tmp_path):
    nucleo = criar_nucleo()
    app = create_app({
        'SECRET_KEY': 'chave-ficticia',
        'CONTAS_HABILITADAS': True, 'OCORRENCIAS_HABILITADAS': True,
        'SETOR_GUARDA_PUBLICO': False, 'CANCELAMENTO_HABILITADO': False,
        'CONTAS_JSON': tmp_path / 'contas.json', 'FOTOS_DIRETORIO': tmp_path / 'fotos',
        'OCORRENCIAS_COMPOSITOR': lambda config: DependenciasOcorrencias(nucleo, ConsultaFake(nucleo)),
    })
    spec = app.test_client().get('/openapi.json').json
    filtros = {p['name'] for p in spec['paths']['/ocorrencias']['get']['parameters']}
    assert 'situacao_guarda' not in filtros
    assert 'setor_guarda' not in filtros
    status_schema = (
        spec['paths']['/ocorrencias/{ocorrencia_id}/status']['post']['requestBody']
        ['content']['application/x-www-form-urlencoded']['schema']['properties']['novo_status']
    )
    assert status_schema['enum'] == ['ABERTO', 'RESOLVIDO']
