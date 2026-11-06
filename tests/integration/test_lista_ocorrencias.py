"""Modelo, núcleo e Lista reais; adaptador de memória só para estes testes.

Não representa sincronização de produção com JSON/AVL (SCRUM-13).
"""

from datetime import date

import pytest

from app.erros import ConflitoAlteracao, ErroPersistencia, ErroValidacao
from app.models.ocorrencia import Ocorrencia, SituacaoGuarda, StatusOcorrencia, TipoOcorrencia
from app.services.nucleo_ocorrencias import NucleoOcorrencias
from app.structures.lista_dinamica import ListaDinamica

pytestmark = pytest.mark.integracao


class ArmazenamentoListaTeste:
    """Permite verificar a integração sem antecipar repositório ou AVL."""

    def __init__(self):
        self.lista = ListaDinamica[Ocorrencia](capacidade_inicial=1)
        self.falhar = False

    def obter(self, ocorrencia_id):
        return self.lista.buscar(lambda item: item.id == ocorrencia_id)

    def listar(self):
        return tuple(self.lista)

    def aplicar(self, lote):
        nova_lista = ListaDinamica[Ocorrencia](capacidade_inicial=1)
        for item in lote.preparar_estado(self.lista):
            nova_lista.inserir(item)
        if self.falhar:
            raise ErroPersistencia("Falha simulada antes da publicação.")
        self.lista = nova_lista


def dados(**alteracoes):
    resultado = {"tipo": "PERDIDO", "nome": "Garrafa", "categoria": "Recipientes",
                 "data_ocorrencia": date(2026, 10, 19), "local_ocorrencia": "Biblioteca",
                 "foto_referencia": "ocorrencias/garrafa.jpg"}
    resultado.update(alteracoes)
    return resultado


def cadastrar(nucleo, **alteracoes):
    lote = nucleo.preparar_cadastro(dados(**alteracoes))
    nucleo.confirmar(lote)
    return lote.alteracoes[0].id


def ambiente():
    armazenamento = ArmazenamentoListaTeste()
    return NucleoOcorrencias(armazenamento), armazenamento


def test_filtros_na_lista_e_no_nucleo_distinguem_local_guarda_e_nao_entregue():
    nucleo, armazenamento = ambiente()
    perdido = cadastrar(nucleo)
    guardado = cadastrar(nucleo, tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 9")
    nao_entregue = cadastrar(nucleo, tipo="ENCONTRADO", categoria="Outros", local_ocorrencia="Bloco 9")
    lista = armazenamento.lista

    casos = (
        ({"tipo": "PERDIDO"}, lambda o: o.tipo is TipoOcorrencia.PERDIDO, (perdido,)),
        ({"categoria": "Outros"}, lambda o: o.categoria == "Outros", (nao_entregue,)),
        ({"local_ocorrencia": "Biblioteca"}, lambda o: o.local_ocorrencia == "Biblioteca", (perdido, guardado)),
        ({"setor_guarda": "Bloco 9"}, lambda o: o.setor_guarda == "Bloco 9", (guardado,)),
        ({"situacao_guarda": "AINDA_NAO_ENTREGUE"},
         lambda o: o.situacao_guarda is SituacaoGuarda.AINDA_NAO_ENTREGUE, (nao_entregue,)),
        ({"status": "ABERTO"}, lambda o: o.status is StatusOcorrencia.ABERTO,
         (perdido, guardado, nao_entregue)),
    )
    for filtros, predicado, ids in casos:
        assert tuple(item.id for item in lista.filtrar(predicado)) == ids
        assert tuple(item.id for item in nucleo.listar(filtros)) == ids
    assert tuple(item.id for item in nucleo.listar({"tipo": "ENCONTRADO", "categoria": "Outros"})) == (nao_entregue,)
    assert len(lista) == 3


def test_correcao_por_posicao_preserva_ids_fotos_recebimento_e_outros_registros():
    lista = ListaDinamica[Ocorrencia](capacidade_inicial=1)
    primeiro = Ocorrencia.criar(dados())
    achado = Ocorrencia.criar(dados(tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 9",
                                   data_recebimento=date(2026, 10, 21)))
    lista.inserir(primeiro)
    lista.inserir(achado)
    indice = lista.buscar_indice(lambda item: item.id == achado.id)
    corrigido = achado.corrigir({"setor_guarda": "Bloco 10", "data_ocorrencia": date(2026, 10, 18)})
    lista.atualizar(indice, corrigido)
    assert tuple(item.id for item in lista) == (primeiro.id, achado.id)
    assert lista.obter(0) is primeiro
    assert lista.obter(1).setor_guarda == "Bloco 10"
    assert lista.obter(1).data_recebimento == date(2026, 10, 21)
    assert lista.obter(1).foto_referencia == achado.foto_referencia
    assert lista.obter(1).local_ocorrencia == "Biblioteca"
    assert tuple(lista.filtrar(lambda item: item.setor_guarda == "Bloco 9")) == ()


def test_nucleo_publica_pares_e_exclusao_na_lista_sem_perder_outros_ids():
    nucleo, armazenamento = ambiente()
    perdido = cadastrar(nucleo)
    achado = cadastrar(nucleo, tipo="ENCONTRADO")
    terceiro = cadastrar(nucleo, nome="Caderno")
    nucleo.confirmar(nucleo.preparar_vinculo(perdido, achado))
    nucleo.confirmar(nucleo.preparar_resolucao(achado))
    assert tuple(item.id for item in nucleo.listar({"status": "RESOLVIDO"})) == (perdido, achado)
    nucleo.confirmar(nucleo.preparar_reabertura(perdido))
    assert tuple(item.id for item in armazenamento.lista) == (perdido, achado, terceiro)
    assert all(item.status is StatusOcorrencia.ABERTO for item in armazenamento.lista)
    nucleo.confirmar(nucleo.preparar_exclusao(perdido))
    assert tuple(item.id for item in armazenamento.lista) == (achado, terceiro)
    assert nucleo.obter(achado).vinculo_id is None
    assert nucleo.obter(terceiro).nome == "Caderno"


def test_foto_invalida_e_conflito_nao_modificam_lista_atual():
    nucleo, armazenamento = ambiente()
    with pytest.raises(ErroValidacao):
        cadastrar(nucleo, foto_referencia="")
    assert len(armazenamento.lista) == 0
    item_id = cadastrar(nucleo)
    lote_antigo = nucleo.preparar_edicao(item_id, {"cor": "vermelho"})
    nucleo.confirmar(nucleo.preparar_edicao(item_id, {"cor": "azul"}))
    antes = armazenamento.lista
    with pytest.raises(ConflitoAlteracao):
        nucleo.confirmar(lote_antigo)
    assert armazenamento.lista is antes
    assert nucleo.obter(item_id).cor == "azul"


def test_falha_e_desistencia_preservam_lista_e_par_inteiros():
    nucleo, armazenamento = ambiente()
    perdido = cadastrar(nucleo)
    achado = cadastrar(nucleo, tipo="ENCONTRADO")
    nucleo.confirmar(nucleo.preparar_vinculo(perdido, achado))
    antes = armazenamento.lista
    lote = nucleo.preparar_resolucao(perdido)
    assert armazenamento.lista is antes  # Desistir: não confirmar.
    armazenamento.falhar = True
    with pytest.raises(ErroPersistencia):
        nucleo.confirmar(lote)
    assert armazenamento.lista is antes
    assert all(item.status is StatusOcorrencia.ABERTO for item in armazenamento.lista)


def test_snapshot_do_codec_reconstroi_lista_preservando_todos_os_campos():
    nucleo, armazenamento = ambiente()
    cadastrar(nucleo)
    cadastrar(nucleo, tipo="ENCONTRADO", situacao_guarda="EM_SETOR", setor_guarda="Bloco 10")
    recarregada = ListaDinamica[Ocorrencia](capacidade_inicial=1)
    for item in armazenamento.lista:
        recarregada.inserir(Ocorrencia.de_registro(item.para_registro()))
    assert tuple(recarregada) == tuple(armazenamento.lista)
    assert recarregada.capacidade == 2
