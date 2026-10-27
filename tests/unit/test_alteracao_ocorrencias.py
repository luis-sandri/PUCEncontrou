"""Precondições e integridade do lote real, sem infraestrutura externa."""

from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest

from app.erros import ConflitoAlteracao, ErroValidacao
from app.models.alteracao_ocorrencias import AlteracaoOcorrencia, LoteOcorrencias
from app.models.ocorrencia import Ocorrencia, StatusOcorrencia


def item(tipo="PERDIDO"):
    return Ocorrencia.criar({"tipo": tipo, "nome": "Caderno", "categoria": "Materiais",
                            "data_ocorrencia": date(2026, 10, 19),
                            "local_ocorrencia": "Bloco 10", "foto_referencia": "fotos/caderno.jpg"})


@pytest.mark.parametrize("anteriores,posteriores", [(None, None), ("inválido", None), (None, 1)])
def test_alteracao_rejeita_estados_ausentes_ou_invalidos(anteriores, posteriores):
    with pytest.raises(ErroValidacao):
        AlteracaoOcorrencia(anteriores, posteriores)


def test_alteracao_rejeita_troca_de_id_ou_tipo():
    original = item()
    with pytest.raises(ErroValidacao):
        AlteracaoOcorrencia(original, replace(original, id="novo"))
    with pytest.raises(ErroValidacao):
        AlteracaoOcorrencia(original, replace(original, tipo="ENCONTRADO"))


def test_lote_imutavel_nao_aceita_array_mutavel_vazio_ou_id_duplicado():
    alteracao = AlteracaoOcorrencia(None, item())
    for alteracoes in ([], (), (alteracao, alteracao), ("inválido",)):
        with pytest.raises(ErroValidacao):
            LoteOcorrencias(alteracoes)
    lote = LoteOcorrencias((alteracao,))
    with pytest.raises(FrozenInstanceError):
        lote.alteracoes = ()


def test_snapshot_rejeita_ids_duplicados_e_itens_nao_validados():
    original = item()
    lote = LoteOcorrencias((AlteracaoOcorrencia(original, None),))
    for estado in ((original, original), (original, object())):
        with pytest.raises(ErroValidacao):
            lote.preparar_estado(estado)


def test_publicacao_parcial_de_vinculo_ou_resolucao_e_rejeitada():
    perdido, encontrado = item(), item("ENCONTRADO")
    vinculo_so_de_um_lado = LoteOcorrencias((AlteracaoOcorrencia(perdido, replace(perdido, vinculo_id=encontrado.id)),))
    with pytest.raises(ErroValidacao):
        vinculo_so_de_um_lado.preparar_estado((perdido, encontrado))
    perdido, encontrado = replace(perdido, vinculo_id=encontrado.id), replace(encontrado, vinculo_id=perdido.id)
    resolucao_so_de_um_lado = LoteOcorrencias((AlteracaoOcorrencia(perdido, replace(perdido, status=StatusOcorrencia.RESOLVIDO)),))
    with pytest.raises(ErroValidacao):
        resolucao_so_de_um_lado.preparar_estado((perdido, encontrado))


def test_preparacao_nao_modifica_origem_e_preserva_demais_ids_e_ordem():
    primeiro, segundo, terceiro = item(), item(), item()
    origem = [primeiro, segundo, terceiro]
    alterado = segundo.corrigir({"nome": "Caderno grande"})
    lote = LoteOcorrencias((AlteracaoOcorrencia(segundo, alterado), AlteracaoOcorrencia(primeiro, None)))
    assert lote.preparar_estado(origem) == (alterado, terceiro)
    assert origem == [primeiro, segundo, terceiro]


def test_editar_registro_excluido_rejeita_lote_obsoleto():
    original = item()
    lote = LoteOcorrencias((AlteracaoOcorrencia(original, original.corrigir({"cor": "azul"})),))
    with pytest.raises(ConflitoAlteracao):
        lote.preparar_estado(())
