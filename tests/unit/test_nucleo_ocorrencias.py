"""Núcleo real com armazenamento transacional fake, exclusivo destes testes."""

from dataclasses import replace
from datetime import date

import pytest

from app.erros import ConflitoAlteracao, ErroPersistencia, ErroValidacao, OcorrenciaNaoEncontrada
from app.models.ocorrencia import Ocorrencia, StatusOcorrencia
from app.services import nucleo_ocorrencias as nucleo


class ArmazenamentoFake:
    """Substitui somente a integração SCRUM-13; não é a Lista de produção."""

    def __init__(self, *ocorrencias):
        self.registros = tuple(ocorrencias)
        self.falhar = False

    def obter(self, ocorrencia_id):
        return next((item for item in self.registros if item.id == ocorrencia_id), None)

    def listar(self):
        return iter(self.registros)

    def aplicar(self, lote):
        novo_estado = lote.preparar_estado(self.registros)
        if self.falhar:
            raise ErroPersistencia("Falha simulada antes da publicação.")
        self.registros = novo_estado


def dados(**alteracoes):
    resultado = {"tipo": "PERDIDO", "nome": "Mouse", "categoria": "Eletrônicos",
                 "local_ocorrencia": "Biblioteca", "data_ocorrencia": date(2026, 10, 19),
                 "foto_referencia": "ocorrencias/mouse.jpg"}
    resultado.update(alteracoes)
    return resultado


@pytest.fixture
def ambiente():
    armazenamento = ArmazenamentoFake()
    return nucleo.NucleoOcorrencias(armazenamento), armazenamento


def cadastrar(servico, **alteracoes):
    lote = servico.preparar_cadastro(dados(**alteracoes))
    item = lote.alteracoes[0].posterior
    servico.confirmar(lote)
    return item


def par(servico):
    perdido = cadastrar(servico)
    encontrado = cadastrar(servico, tipo="ENCONTRADO")
    servico.confirmar(servico.preparar_vinculo(perdido.id, encontrado.id))
    return perdido.id, encontrado.id


def test_lista_vazia_busca_ausente_e_cadastro_so_muda_apos_confirmacao(ambiente):
    servico, armazenamento = ambiente
    assert tuple(servico.listar()) == ()
    with pytest.raises(OcorrenciaNaoEncontrada):
        servico.obter("inexistente")
    lote = servico.preparar_cadastro(dados())
    assert armazenamento.registros == ()
    assert lote.alteracoes[0].anterior is None
    servico.confirmar(lote)
    item = lote.alteracoes[0].posterior
    assert servico.obter(item.id) == item
    assert tuple(servico.listar()) == (item,)


def test_crud_preserva_identidade_e_informa_data_antiga_para_avl(ambiente):
    servico, _ = ambiente
    item = cadastrar(servico)
    lote = servico.preparar_edicao(item.id, {"nome": "Mouse preto", "data_ocorrencia": date(2026, 10, 18)})
    alteracao = lote.alteracoes[0]
    assert alteracao.anterior.data_ocorrencia == date(2026, 10, 19)
    assert alteracao.posterior.data_ocorrencia == date(2026, 10, 18)
    assert alteracao.id == item.id
    assert servico.obter(item.id).nome == "Mouse"
    servico.confirmar(lote)
    assert servico.obter(item.id).nome == "Mouse preto"
    exclusao = servico.preparar_exclusao(item.id)
    assert exclusao.alteracoes[0].anterior.id == item.id
    assert exclusao.alteracoes[0].posterior is None
    servico.confirmar(exclusao)
    assert tuple(servico.listar()) == ()


def test_filtros_combinam_campos_sem_confundir_local_e_guarda(ambiente):
    servico, _ = ambiente
    perdido = cadastrar(servico)
    achado = cadastrar(servico, tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 9")
    nao_entregue = cadastrar(servico, tipo="ENCONTRADO", local_ocorrencia="Bloco 9", categoria="Outros")
    assert tuple(servico.listar({"local_ocorrencia": "Biblioteca"})) == (perdido, achado)
    assert tuple(servico.listar({"setor_guarda": "Bloco 9"})) == (achado,)
    assert tuple(servico.listar({"situacao_guarda": "AINDA_NAO_ENTREGUE"})) == (nao_entregue,)
    assert tuple(servico.listar({"tipo": "ENCONTRADO", "categoria": "Eletrônicos", "status": "ABERTO"})) == (achado,)
    assert tuple(servico.listar({"categoria": "Inexistente"})) == ()


@pytest.mark.parametrize("filtros", [{"local": "x"}, {"tipo": "OUTRO"}, {"status": 2},
                                    {"categoria": None}, {"situacao_guarda": "X"}, {"setor_guarda": []}])
def test_filtro_invalido_nao_e_ignorado(ambiente, filtros):
    with pytest.raises(ErroValidacao):
        tuple(ambiente[0].listar(filtros))


def test_vincular_nao_resolve_e_devolucao_reabertura_atualizam_ambos(ambiente):
    servico, _ = ambiente
    perdido_id, encontrado_id = par(servico)
    assert servico.obter(perdido_id).status is StatusOcorrencia.ABERTO
    assert servico.obter(perdido_id).vinculo_id == encontrado_id
    assert servico.obter(encontrado_id).vinculo_id == perdido_id
    lote = servico.preparar_resolucao(encontrado_id)
    assert len(lote.alteracoes) == 2
    assert servico.obter(perdido_id).status is StatusOcorrencia.ABERTO
    servico.confirmar(lote)
    assert [servico.obter(i).status for i in (perdido_id, encontrado_id)] == [StatusOcorrencia.RESOLVIDO] * 2
    servico.confirmar(servico.preparar_reabertura(perdido_id))
    assert [servico.obter(i).status for i in (perdido_id, encontrado_id)] == [StatusOcorrencia.ABERTO] * 2
    assert servico.obter(perdido_id).vinculo_id == encontrado_id


def test_desistir_e_falha_de_aplicacao_preservam_par(ambiente):
    servico, armazenamento = ambiente
    perdido_id, encontrado_id = par(servico)
    antes = armazenamento.registros
    servico.preparar_resolucao(perdido_id)  # Usuário desiste sem confirmar.
    assert armazenamento.registros == antes
    lote = servico.preparar_resolucao(encontrado_id)
    armazenamento.falhar = True
    with pytest.raises(ErroPersistencia):
        servico.confirmar(lote)
    assert armazenamento.registros == antes


@pytest.mark.parametrize("resolvido", [False, True])
def test_exclusao_fisica_limpa_vinculo_e_preserva_estado_do_parceiro(ambiente, resolvido):
    servico, _ = ambiente
    perdido_id, encontrado_id = par(servico)
    if resolvido:
        servico.confirmar(servico.preparar_resolucao(perdido_id))
    parceiro = servico.obter(encontrado_id)
    lote = servico.preparar_exclusao(perdido_id)
    assert len(lote.alteracoes) == 2
    servico.confirmar(lote)
    with pytest.raises(OcorrenciaNaoEncontrada):
        servico.obter(perdido_id)
    assert servico.obter(encontrado_id) == replace(parceiro, vinculo_id=None)
    assert len(tuple(servico.listar())) == 1


def test_falha_exclusao_nao_apaga_nem_desvincula_metade(ambiente):
    servico, armazenamento = ambiente
    perdido_id, _ = par(servico)
    antes = armazenamento.registros
    lote = servico.preparar_exclusao(perdido_id)
    armazenamento.falhar = True
    with pytest.raises(ErroPersistencia):
        servico.confirmar(lote)
    assert armazenamento.registros == antes


def test_lote_obsoleto_nao_sobrescreve_correcao_mais_recente(ambiente):
    servico, _ = ambiente
    item = cadastrar(servico)
    antigo = servico.preparar_edicao(item.id, {"cor": "branco"})
    servico.confirmar(servico.preparar_edicao(item.id, {"cor": "preto"}))
    with pytest.raises(ConflitoAlteracao):
        servico.confirmar(antigo)
    assert servico.obter(item.id).cor == "preto"


def test_lote_de_par_obsoleto_rejeita_todos_os_registros(ambiente):
    servico, armazenamento = ambiente
    perdido_id, encontrado_id = par(servico)
    lote = servico.preparar_resolucao(perdido_id)
    servico.confirmar(servico.preparar_edicao(encontrado_id, {"nome": "Mouse sem fio"}))
    antes = armazenamento.registros
    with pytest.raises(ConflitoAlteracao):
        servico.confirmar(lote)
    assert armazenamento.registros == antes


def test_mesmo_cadastro_nao_e_aplicado_duas_vezes(ambiente):
    servico, _ = ambiente
    lote = servico.preparar_cadastro(dados())
    servico.confirmar(lote)
    with pytest.raises(ConflitoAlteracao):
        servico.confirmar(lote)
    assert len(tuple(servico.listar())) == 1


def test_transicoes_isoladas_e_cancelamento_de_par_bloqueado(ambiente):
    servico, armazenamento = ambiente
    item = cadastrar(servico)
    servico.confirmar(servico.preparar_cancelamento(item.id))
    assert servico.obter(item.id).status is StatusOcorrencia.CANCELADO
    with pytest.raises(ErroValidacao):
        servico.preparar_resolucao(item.id)
    servico.confirmar(servico.preparar_reabertura(item.id))
    servico.confirmar(servico.preparar_resolucao(item.id))
    with pytest.raises(ErroValidacao):
        servico.preparar_cancelamento(item.id)
    perdido_id, _ = par(servico)
    antes = armazenamento.registros
    with pytest.raises(ErroValidacao):
        servico.preparar_cancelamento(perdido_id)
    assert armazenamento.registros == antes


def test_vinculo_rejeita_tipos_iguais_terceiro_parceiro_e_encerrados(ambiente):
    servico, _ = ambiente
    perdido_id, encontrado_id = par(servico)
    outro = cadastrar(servico)
    with pytest.raises(ErroValidacao):
        servico.preparar_vinculo(perdido_id, outro.id)
    with pytest.raises(ErroValidacao):
        servico.preparar_vinculo(outro.id, encontrado_id)
    achado = cadastrar(servico, tipo="ENCONTRADO")
    servico.confirmar(servico.preparar_cancelamento(outro.id))
    with pytest.raises(ErroValidacao):
        servico.preparar_vinculo(outro.id, achado.id)


def test_operacoes_inexistentes_rejeitam_sem_mudar_estado(ambiente):
    servico, armazenamento = ambiente
    for operacao in (servico.preparar_exclusao, servico.preparar_resolucao,
                     servico.preparar_cancelamento, servico.preparar_reabertura):
        with pytest.raises(OcorrenciaNaoEncontrada):
            operacao("ausente")
    with pytest.raises(OcorrenciaNaoEncontrada):
        servico.preparar_edicao("ausente", {"nome": "x"})
    assert armazenamento.registros == ()


def test_integridade_rejeita_par_quebrado_sem_preparar_metade():
    item = replace(Ocorrencia.criar(dados()), vinculo_id="ausente")
    armazenamento = ArmazenamentoFake(item)
    servico = nucleo.NucleoOcorrencias(armazenamento)
    with pytest.raises(ErroValidacao):
        servico.preparar_resolucao(item.id)
    assert armazenamento.registros == (item,)
