"""Testes de unidade da Árvore AVL manual de índice temporal."""

from datetime import date

import pytest

from app.structures.avl import ArvoreAVL, _NoAVL


def _verificar_invariantes_avl(no: _NoAVL | None) -> tuple[int, list[tuple[date, str]]]:
    """Verifica recursivamente propriedades de ABB, alturas e fator de balanceamento."""
    if no is None:
        return 0, []

    altura_esq, chaves_esq = _verificar_invariantes_avl(no.esquerda)
    altura_dir, chaves_dir = _verificar_invariantes_avl(no.direita)

    altura_esperada = 1 + max(altura_esq, altura_dir)
    assert no.altura == altura_esperada, (
        f"Altura incorreta no nó {no.chave}: esperada {altura_esperada}, atual {no.altura}"
    )

    fator = altura_esq - altura_dir
    assert -1 <= fator <= 1, (
        f"Nó {no.chave} desbalanceado com fator {fator}"
    )

    for chave_e in chaves_esq:
        assert chave_e < no.chave, f"Violação de ABB à esquerda de {no.chave}: {chave_e}"
    for chave_d in chaves_dir:
        assert chave_d > no.chave, f"Violação de ABB à direita de {no.chave}: {chave_d}"

    return altura_esperada, [*chaves_esq, no.chave, *chaves_dir]


def test_indice_vazio_retorna_iterador_vazio():
    arvore = ArvoreAVL()
    assert len(arvore) == 0
    resultado = list(arvore.buscar_periodo(date(2026, 1, 1), date(2026, 12, 31)))
    assert resultado == []


def test_rotacao_ll_direita():
    arvore = ArvoreAVL()
    arvore.inserir(date(2026, 5, 30), "oc-3")
    arvore.inserir(date(2026, 5, 20), "oc-2")
    arvore.inserir(date(2026, 5, 10), "oc-1")

    assert arvore._raiz is not None
    assert arvore._raiz.chave == (date(2026, 5, 20), "oc-2")
    _verificar_invariantes_avl(arvore._raiz)


def test_rotacao_rr_esquerda():
    arvore = ArvoreAVL()
    arvore.inserir(date(2026, 5, 10), "oc-1")
    arvore.inserir(date(2026, 5, 20), "oc-2")
    arvore.inserir(date(2026, 5, 30), "oc-3")

    assert arvore._raiz is not None
    assert arvore._raiz.chave == (date(2026, 5, 20), "oc-2")
    _verificar_invariantes_avl(arvore._raiz)


def test_rotacao_lr_esquerda_direita():
    arvore = ArvoreAVL()
    arvore.inserir(date(2026, 5, 30), "oc-3")
    arvore.inserir(date(2026, 5, 10), "oc-1")
    arvore.inserir(date(2026, 5, 20), "oc-2")

    assert arvore._raiz is not None
    assert arvore._raiz.chave == (date(2026, 5, 20), "oc-2")
    _verificar_invariantes_avl(arvore._raiz)


def test_rotacao_rl_direita_esquerda():
    arvore = ArvoreAVL()
    arvore.inserir(date(2026, 5, 10), "oc-1")
    arvore.inserir(date(2026, 5, 30), "oc-3")
    arvore.inserir(date(2026, 5, 20), "oc-2")

    assert arvore._raiz is not None
    assert arvore._raiz.chave == (date(2026, 5, 20), "oc-2")
    _verificar_invariantes_avl(arvore._raiz)


def test_multiplos_ids_na_mesma_data_e_idempotencia_de_insercao():
    arvore = ArvoreAVL()
    mesmo_dia = date(2026, 6, 15)

    arvore.inserir(mesmo_dia, "oc-b")
    arvore.inserir(mesmo_dia, "oc-a")
    arvore.inserir(mesmo_dia, "oc-c")
    # Reinserir par existente não deve duplicar
    arvore.inserir(mesmo_dia, "oc-a")

    assert len(arvore) == 3
    _verificar_invariantes_avl(arvore._raiz)

    ids = list(arvore.buscar_periodo(mesmo_dia, mesmo_dia))
    assert ids == ["oc-a", "oc-b", "oc-c"]


def test_buscar_periodo_limites_inclusivos_e_ordem_por_data():
    arvore = ArvoreAVL()
    dados = [
        (date(2026, 3, 1), "oc-01"),
        (date(2026, 3, 5), "oc-05-b"),
        (date(2026, 3, 5), "oc-05-a"),
        (date(2026, 3, 10), "oc-10"),
        (date(2026, 3, 15), "oc-15"),
        (date(2026, 3, 20), "oc-20"),
    ]
    for data_oc, oc_id in dados:
        arvore.inserir(data_oc, oc_id)

    _verificar_invariantes_avl(arvore._raiz)

    resultado = list(arvore.buscar_periodo(date(2026, 3, 5), date(2026, 3, 15)))
    assert resultado == ["oc-05-a", "oc-05-b", "oc-10", "oc-15"]


def test_buscar_periodo_inicio_maior_que_fim_levanta_value_error():
    arvore = ArvoreAVL()
    arvore.inserir(date(2026, 4, 10), "oc-1")

    with pytest.raises(ValueError, match="início"):
        arvore.buscar_periodo(date(2026, 4, 12), date(2026, 4, 10))


def test_remocao_preserva_outros_ids_e_balanceamento():
    arvore = ArvoreAVL()
    pares = [
        (date(2026, 1, d), f"oc-{d:02d}") for d in range(1, 16)
    ] + [
        (date(2026, 1, 5), "oc-05-extra"),
        (date(2026, 1, 10), "oc-10-extra"),
    ]
    for data_oc, oc_id in pares:
        arvore.inserir(data_oc, oc_id)

    assert len(arvore) == 17
    _verificar_invariantes_avl(arvore._raiz)

    # Remover par inexistente na mesma data não remove os demais
    arvore.remover(date(2026, 1, 5), "oc-inexistente")
    assert len(arvore) == 17
    assert list(arvore.buscar_periodo(date(2026, 1, 5), date(2026, 1, 5))) == [
        "oc-05",
        "oc-05-extra",
    ]

    # Remover nó folha, nó com 1 filho e nós com 2 filhos (incluindo raiz)
    for data_oc, oc_id in [
        (date(2026, 1, 1), "oc-01"),
        (date(2026, 1, 5), "oc-05"),
        (date(2026, 1, 8), "oc-08"),
        (date(2026, 1, 12), "oc-12"),
    ]:
        arvore.remover(data_oc, oc_id)
        _verificar_invariantes_avl(arvore._raiz)

    assert len(arvore) == 13
    # O outro ID do dia 5 permanece intacto
    assert list(arvore.buscar_periodo(date(2026, 1, 5), date(2026, 1, 5))) == [
        "oc-05-extra"
    ]
