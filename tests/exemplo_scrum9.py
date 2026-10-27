"""Demonstração da Lista real: python -m tests.exemplo_scrum9 na raiz."""

from datetime import date

from app.models.ocorrencia import Ocorrencia, SituacaoGuarda, TipoOcorrencia
from app.structures.lista_dinamica import ListaDinamica


def main() -> None:
    lista = ListaDinamica[Ocorrencia](capacidade_inicial=2)
    dados = {
        "tipo": "PERDIDO", "nome": "Garrafa", "categoria": "Recipientes",
        "data_ocorrencia": date(2026, 10, 19), "local_ocorrencia": "Biblioteca",
        "foto_referencia": "ocorrencias/garrafa.jpg",
    }
    perdido = Ocorrencia.criar(dados)
    guardado = Ocorrencia.criar({
        **dados, "tipo": "ENCONTRADO", "situacao_guarda": "EM_SETOR",
        "setor_guarda": "Bloco 9", "data_recebimento": date(2026, 10, 21),
    })
    nao_entregue = Ocorrencia.criar({**dados, "tipo": "ENCONTRADO", "nome": "Caderno"})
    for item in (perdido, guardado, nao_entregue):
        lista.inserir(item)
    assert len(lista) == 3
    assert lista.capacidade == 4
    print(f"Insercao: {len(lista)} registros; capacidade expandida de 2 para {lista.capacidade}.")

    encontrados = lista.filtrar(lambda item: item.tipo is TipoOcorrencia.ENCONTRADO)
    guardados = lista.filtrar(lambda item: item.setor_guarda == "Bloco 9")
    sem_entrega = lista.filtrar(lambda item: item.situacao_guarda is SituacaoGuarda.AINDA_NAO_ENTREGUE)
    assert len(encontrados) == 2 and len(guardados) == 1 and len(sem_entrega) == 1
    print("Filtros: 2 encontrados, 1 no Bloco 9, 1 ainda nao entregue.")

    indice = lista.buscar_indice(lambda item: item.id == guardado.id)
    assert indice is not None
    lista.atualizar(indice, guardado.corrigir({
        "setor_guarda": "Bloco 10", "data_ocorrencia": date(2026, 10, 18),
    }))
    corrigido = lista.buscar(lambda item: item.id == guardado.id)
    assert corrigido is not None
    assert corrigido.data_recebimento == date(2026, 10, 21)
    assert corrigido.local_ocorrencia == "Biblioteca"
    assert len(lista) == 3
    print("Correcao: mesmo ID, guarda no Bloco 10 e recebimento preservado.")

    assert lista.remover(0).id == perdido.id
    assert tuple(item.id for item in lista) == (guardado.id, nao_entregue.id)
    assert lista.buscar(lambda item: item.id == perdido.id) is None
    print("Remocao: 2 registros preservados em ordem, sem trocar seus IDs.")
    print("Demonstracao concluida com a Lista manual real; nenhum arquivo de dados foi criado.")


if __name__ == "__main__":
    main()
