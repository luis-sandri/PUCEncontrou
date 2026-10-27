"""Contrato do modelo: validação e codec independentes de Flask e arquivos."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from uuid import UUID

import pytest

from app.erros import ErroValidacao
from app.models import ocorrencia as modelo


def dados_ocorrencia(**alteracoes):
    dados = {
        "tipo": "PERDIDO",
        "nome": "Garrafa azul",
        "categoria": "Garrafas",
        "data_ocorrencia": date(2026, 10, 19),
        "local_ocorrencia": "Biblioteca",
        "foto_referencia": "ocorrencias/garrafa.jpg",
    }
    dados.update(alteracoes)
    return dados


def criar(**alteracoes):
    return modelo.Ocorrencia.criar(dados_ocorrencia(**alteracoes))


def test_criacao_gera_ids_unicos_e_status_aberto():
    primeira, segunda = criar(), criar()
    assert UUID(primeira.id)
    assert primeira.id != segunda.id
    assert primeira.status is modelo.StatusOcorrencia.ABERTO
    assert primeira.vinculo_id is None
    assert primeira.cor is None
    assert primeira.descricao is None


@pytest.mark.parametrize("tipo", ["PERDIDO", "ENCONTRADO"])
@pytest.mark.parametrize("foto", [None, "", "   ", 12, "/foto.jpg", "C:/foto.jpg",
                                       "../foto.jpg", "a/../foto.jpg", "a\\foto.jpg",
                                       "https://site/foto.jpg", "a/./foto.jpg", "a\x00.jpg"])
def test_ambos_tipos_rejeitam_foto_ausente_ou_referencia_invalida(tipo, foto):
    with pytest.raises(ErroValidacao, match="foto_referencia"):
        criar(tipo=tipo, foto_referencia=foto)


@pytest.mark.parametrize("campo", ["nome", "categoria", "data_ocorrencia", "local_ocorrencia", "foto_referencia"])
def test_criacao_rejeita_campo_obrigatorio_ausente(campo):
    dados = dados_ocorrencia()
    del dados[campo]
    with pytest.raises(ErroValidacao, match=campo):
        modelo.Ocorrencia.criar(dados)


@pytest.mark.parametrize("alteracoes", [
    {"tipo": "ACHADO"}, {"nome": 1}, {"categoria": " "},
    {"descricao": []}, {"cor": False}, {"data_ocorrencia": "2026-10-19"},
    {"data_ocorrencia": datetime(2026, 10, 19)}, {"local_ocorrencia": None},
    {"destinacao_a_verificar": "false"}, {"qualquer_campo": "x"},
    {"id": "imposto"}, {"status": "RESOLVIDO"}, {"vinculo_id": "x"},
])
def test_criacao_rejeita_tipos_invalidos_e_campos_controlados(alteracoes):
    with pytest.raises(ErroValidacao):
        criar(**alteracoes)


def test_campos_textuais_sao_normalizados_sem_fixar_categorias():
    item = criar(nome="  Mouse  ", categoria=" Categoria futura ", cor=" preta ")
    assert (item.nome, item.categoria, item.cor) == ("Mouse", "Categoria futura", "preta")


def test_achado_guarda_local_e_recebimento_distintos():
    item = criar(tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 9",
                 data_recebimento=date(2026, 10, 21), destinacao_a_verificar=True)
    assert item.local_ocorrencia == "Biblioteca"
    assert item.setor_guarda == "Bloco 9"
    assert item.data_recebimento == date(2026, 10, 21)
    assert item.data_ocorrencia == date(2026, 10, 19)
    assert item.destinacao_a_verificar is True
    corrigido = item.corrigir({"setor_guarda": "Bloco 10", "data_ocorrencia": date(2026, 10, 18)})
    assert corrigido.id == item.id
    assert corrigido.data_recebimento == date(2026, 10, 21)
    assert corrigido.local_ocorrencia == "Biblioteca"


def test_achado_ainda_nao_entregue_nao_inventa_recebimento():
    item = criar(tipo="ENCONTRADO")
    assert item.situacao_guarda is modelo.SituacaoGuarda.AINDA_NAO_ENTREGUE
    assert item.setor_guarda is None
    assert item.data_recebimento is None
    assert item.corrigir({"data_ocorrencia": date(2026, 10, 1)}).data_recebimento is None


@pytest.mark.parametrize("alteracoes", [
    {"tipo": "PERDIDO", "setor_guarda": "Bloco 9"},
    {"tipo": "PERDIDO", "situacao_guarda": "EM_SETOR"},
    {"tipo": "PERDIDO", "data_recebimento": date(2026, 10, 21)},
    {"tipo": "PERDIDO", "destinacao_a_verificar": True},
    {"tipo": "ENCONTRADO", "situacao_guarda": "EM_SETOR"},
    {"tipo": "ENCONTRADO", "setor_guarda": "Bloco 9"},
    {"tipo": "ENCONTRADO", "data_recebimento": date(2026, 10, 21)},
    {"tipo": "ENCONTRADO", "situacao_guarda": "inventada"},
])
def test_guarda_incompativel_e_rejeitada(alteracoes):
    with pytest.raises(ErroValidacao):
        criar(**alteracoes)


def test_modelo_imutavel_e_correcao_preserva_original():
    item = criar()
    with pytest.raises(FrozenInstanceError):
        item.nome = "Outro"
    corrigido = item.corrigir({"nome": "Garrafa térmica"})
    assert item.nome == "Garrafa azul"
    assert corrigido.nome == "Garrafa térmica"
    assert corrigido.id == item.id


@pytest.mark.parametrize("campo,valor", [("id", "novo"), ("tipo", "ENCONTRADO"),
                                        ("status", "CANCELADO"), ("vinculo_id", "x"),
                                        ("foto_referencia", "")])
def test_edicao_nao_contorna_regras(campo, valor):
    with pytest.raises(ErroValidacao):
        criar().corrigir({campo: valor})


def test_codec_round_trip_preserva_id_status_vinculo_e_datas():
    item = replace(criar(tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 9",
                         data_recebimento=date(2026, 10, 22)),
                   status=modelo.StatusOcorrencia.RESOLVIDO, vinculo_id="perdido-42")
    registro = item.para_registro()
    assert registro["data_ocorrencia"] == "2026-10-19"
    assert registro["data_recebimento"] == "2026-10-22"
    assert registro["status"] == "RESOLVIDO"
    assert registro["vinculo_id"] == "perdido-42"
    recarregado = modelo.Ocorrencia.de_registro(json.loads(json.dumps(registro)))
    assert recarregado == item


def test_codec_nulos_preservados_e_registro_independente():
    item = criar()
    registro = item.para_registro()
    assert registro["data_recebimento"] is None
    assert modelo.Ocorrencia.de_registro(registro) == item
    registro["nome"] = "Mudado fora do modelo"
    assert item.nome == "Garrafa azul"


@pytest.mark.parametrize("campo,valor", [("id", ""), ("status", "OUTRO"),
                                        ("tipo", "ACHADO"), ("data_ocorrencia", "2026-02-30"),
                                        ("data_ocorrencia", "20261019"),
                                        ("foto_referencia", None), ("vinculo_id", " "),
                                        ("destinacao_a_verificar", 1), ("campo_novo", "x")])
def test_codec_rejeita_registro_invalido_sem_corrigir_silenciosamente(campo, valor):
    registro = criar().para_registro()
    registro[campo] = valor
    with pytest.raises(ErroValidacao):
        modelo.Ocorrencia.de_registro(registro)


def test_codec_legado_sem_foto_e_rejeitado():
    registro = criar().para_registro()
    del registro["foto_referencia"]
    with pytest.raises(ErroValidacao, match="foto_referencia"):
        modelo.Ocorrencia.de_registro(registro)


def test_vinculo_nao_pode_apontar_para_proprio_id():
    item = criar()
    with pytest.raises(ErroValidacao):
        replace(item, vinculo_id=item.id)


def test_descricao_aceita_multiplas_linhas_mas_referencia_nao_aceita_controles():
    item = criar(descricao="Mouse sem fio\nAdesivo na parte inferior.")
    assert item.descricao == "Mouse sem fio\nAdesivo na parte inferior."
    with pytest.raises(ErroValidacao, match="foto_referencia"):
        criar(foto_referencia="ocorrencias/foto\n.jpg")
