"""Operações acadêmicas da Lista manual; listas prontas só como oráculo de teste."""

import gc
import random
import weakref

import pytest

from app.structures import lista_dinamica as estrutura


def criar_lista(*valores, capacidade=4):
    lista = estrutura.ListaDinamica(capacidade_inicial=capacidade)
    for valor in valores:
        lista.inserir(valor)
    return lista


def test_lista_vazia_separa_tamanho_e_capacidade():
    lista = criar_lista(capacidade=2)
    assert len(lista) == 0
    assert lista.capacidade == 2
    assert tuple(lista) == ()
    assert lista.buscar(lambda valor: True) is None
    assert lista.buscar_indice(lambda valor: True) is None
    assert tuple(lista.filtrar(lambda valor: True)) == ()


@pytest.mark.parametrize("capacidade", [0, -1, -10])
def test_capacidade_precisa_ser_positiva(capacidade):
    with pytest.raises(ValueError):
        criar_lista(capacidade=capacidade)


@pytest.mark.parametrize("capacidade", [None, True, 1.5, "4"])
def test_capacidade_precisa_ser_inteira(capacidade):
    with pytest.raises(TypeError):
        criar_lista(capacidade=capacidade)


def test_insercao_preserva_objetos_e_expande_manualmente_sem_perdas():
    lista = criar_lista(capacidade=2)
    objetos = tuple(object() for _ in range(257))
    for posicao, objeto in enumerate(objetos):
        lista.inserir(objeto)
        assert len(lista) == posicao + 1
        assert lista.obter(posicao) is objeto
    assert lista.capacidade == 512
    assert tuple(lista) == objetos


@pytest.mark.parametrize("indice", [-1, 3, 100])
def test_indices_fora_do_intervalo_nao_modificam_lista(indice):
    lista = criar_lista("a", "b", "c")
    for operacao in (lambda: lista.obter(indice), lambda: lista.remover(indice),
                     lambda: lista.atualizar(indice, "outro")):
        with pytest.raises(IndexError):
            operacao()
    assert tuple(lista) == ("a", "b", "c")


@pytest.mark.parametrize("indice", [True, False, 1.0, "1", None])
def test_indices_nao_inteiros_sao_rejeitados(indice):
    lista = criar_lista(10, 20)
    for operacao in (lambda: lista.obter(indice), lambda: lista.remover(indice),
                     lambda: lista.atualizar(indice, 30)):
        with pytest.raises(TypeError):
            operacao()
    assert tuple(lista) == (10, 20)


def test_operacoes_por_posicao_em_lista_vazia():
    lista = criar_lista()
    for operacao in (lambda: lista.obter(0), lambda: lista.remover(0),
                     lambda: lista.atualizar(0, "x")):
        with pytest.raises(IndexError):
            operacao()


@pytest.mark.parametrize("indice,esperado", [(0, (20, 30, 40)), (1, (10, 30, 40)),
                                           (3, (10, 20, 30))])
def test_remocao_desloca_e_preserva_ordem(indice, esperado):
    lista = criar_lista(10, 20, 30, 40)
    assert lista.remover(indice) == (10, 20, 30, 40)[indice]
    assert tuple(lista) == esperado
    assert len(lista) == 3
    assert lista.capacidade == 4
    lista.inserir(50)
    assert tuple(lista) == (*esperado, 50)


def test_esvaziar_e_reutilizar_lista():
    lista = criar_lista("único", capacidade=1)
    assert lista.remover(0) == "único"
    assert tuple(lista) == ()
    lista.inserir("novo")
    assert lista.obter(0) == "novo"
    assert lista.capacidade == 1


def test_atualizacao_substitui_sem_duplicar_ou_expandir():
    lista = criar_lista("a", "b", capacidade=2)
    lista.atualizar(1, "corrigido")
    assert tuple(lista) == ("a", "corrigido")
    assert len(lista) == 2
    assert lista.capacidade == 2


def test_busca_e_indice_da_primeira_correspondencia():
    lista = criar_lista(2, 4, 6, 4)
    assert lista.buscar(lambda valor: valor == 4) == 4
    assert lista.buscar_indice(lambda valor: valor == 4) == 1
    assert lista.buscar(lambda valor: valor == 9) is None
    assert lista.buscar_indice(lambda valor: valor == 9) is None


def test_none_e_um_elemento_legitimo_nao_uma_posicao_vazia():
    lista = criar_lista(None, "x", capacidade=1)
    assert len(lista) == 2
    assert lista.obter(0) is None
    assert lista.buscar_indice(lambda valor: valor is None) == 0
    assert tuple(lista.filtrar(lambda valor: valor is None)) == (None,)
    assert lista.remover(0) is None
    assert tuple(lista) == ("x",)


def test_filtro_retorna_lista_manual_independente_preservando_ordem():
    lista = criar_lista(1, 2, 3, 4, 5, 6, capacidade=1)
    pares = lista.filtrar(lambda valor: valor % 2 == 0)
    assert isinstance(pares, estrutura.ListaDinamica)
    assert tuple(pares) == (2, 4, 6)
    pares.remover(0)
    pares.inserir(8)
    assert tuple(lista) == (1, 2, 3, 4, 5, 6)
    assert tuple(pares) == (4, 6, 8)


@pytest.mark.parametrize("metodo", ["buscar", "buscar_indice", "filtrar"])
def test_predicado_invalido_e_rejeitado_mesmo_em_lista_vazia(metodo):
    with pytest.raises(TypeError):
        getattr(criar_lista(), metodo)(None)


def test_excecao_do_predicado_nao_e_ocultada_e_preserva_origem():
    lista = criar_lista(1, 2, 3)

    def predicado(valor):
        raise ValueError("Falha no predicado")

    with pytest.raises(ValueError, match="Falha no predicado"):
        lista.filtrar(predicado)
    assert tuple(lista) == (1, 2, 3)


def test_iteradores_independentes_e_percorrimento_repetido():
    lista = criar_lista(1, 2, 3)
    primeiro, segundo = iter(lista), iter(lista)
    assert next(primeiro) == 1
    assert next(primeiro) == 2
    assert next(segundo) == 1
    assert tuple(primeiro) == (3,)
    assert tuple(segundo) == (2, 3)
    assert tuple(lista) == (1, 2, 3)


@pytest.mark.parametrize("operacao", [lambda lista: lista.inserir(4),
                                    lambda lista: lista.remover(1),
                                    lambda lista: lista.atualizar(1, 9)])
def test_mutacao_durante_iteracao_e_detectada(operacao):
    lista = criar_lista(1, 2, 3)
    iterador = iter(lista)
    assert next(iterador) == 1
    operacao(lista)
    with pytest.raises(RuntimeError):
        next(iterador)


def test_iterador_detecta_mutacao_antes_do_primeiro_next():
    lista = criar_lista(1)
    iterador = iter(lista)
    lista.inserir(2)
    with pytest.raises(RuntimeError):
        next(iterador)


def test_busca_nao_aceita_resultado_se_predicado_altera_a_lista():
    lista = criar_lista(10, 20)

    def predicado(valor):
        lista.remover(0)
        return True

    with pytest.raises(RuntimeError):
        lista.buscar(predicado)


def test_remocao_libera_referencia_do_buffer():
    class Registro:
        pass

    registro = Registro()
    referencia = weakref.ref(registro)
    lista = criar_lista(registro)
    del registro
    lista.remover(0)
    gc.collect()
    assert referencia() is None


def test_sequencia_mista_confere_com_oraculo_preservando_todos_os_valores():
    gerador = random.Random(9)
    lista = criar_lista(capacidade=1)
    oraculo = []
    for _ in range(500):
        operacao = gerador.choice(("inserir", "atualizar", "remover"))
        if not oraculo or operacao == "inserir":
            valor = gerador.randrange(10000)
            lista.inserir(valor)
            oraculo.append(valor)
        elif operacao == "atualizar":
            indice = gerador.randrange(len(oraculo))
            valor = gerador.randrange(10000)
            lista.atualizar(indice, valor)
            oraculo[indice] = valor
        else:
            indice = gerador.randrange(len(oraculo))
            assert lista.remover(indice) == oraculo.pop(indice)
        assert len(lista) == len(oraculo)
        assert tuple(lista) == tuple(oraculo)
        assert lista.capacidade >= len(lista)
