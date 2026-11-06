"""Testes de integração entre Persistência JSON, Lista Dinâmica e Árvore AVL (Matheus)."""

from datetime import date

import pytest

from app import create_app
from app.erros import ErroPersistencia, ErroValidacao
from app.models.ocorrencia import Ocorrencia, SituacaoGuarda, StatusOcorrencia, TipoOcorrencia
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON
from app.services.consultas import ServicoConsultaPeriodo
from app.services.inicializacao import (
    ArmazenamentoOcorrencias,
    compor_producao,
    inicializar_ocorrencias,
)
from app.services.nucleo_ocorrencias import NucleoOcorrencias
from app.structures.avl import ArvoreAVL
from app.structures.lista_dinamica import ListaDinamica


def criar_ocorrencia(
    id: str,
    tipo: TipoOcorrencia = TipoOcorrencia.PERDIDO,
    data: date = date(2026, 10, 1),
    foto: str = "fotos/item.png",
    **extra,
) -> Ocorrencia:
    dados = {
        "id": id,
        "tipo": tipo,
        "nome": f"Item {id}",
        "categoria": "Geral",
        "data_ocorrencia": data,
        "local_ocorrencia": "Campus",
        "foto_referencia": foto,
        "descricao": f"Descricao {id}",
        "cor": "Preto",
        "status": StatusOcorrencia.ABERTO,
        **extra,
    }
    return Ocorrencia(**dados)


@pytest.fixture
def ambiente(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)
    repo.inicializar()

    lista = ListaDinamica()
    indice = ArvoreAVL()

    armazenamento = ArmazenamentoOcorrencias(repo, lista, indice)
    nucleo = NucleoOcorrencias(armazenamento)
    consulta = ServicoConsultaPeriodo(indice, armazenamento.obter)

    return repo, lista, indice, armazenamento, nucleo, consulta, caminho


def test_inicializar_com_lista_nao_vazia_rejeita(ambiente):
    repo, lista, indice, _, _, _, _ = ambiente
    lista.inserir(criar_ocorrencia("existente"))
    with pytest.raises(ErroValidacao, match="vazia"):
        inicializar_ocorrencias(repo, lista, indice)


def test_persistencia_apos_reinicio(ambiente):
    repo, lista, indice, armazenamento, nucleo, consulta, caminho = ambiente

    # 1. Cadastra ocorrências através do núcleo
    lote1 = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.PERDIDO,
        "nome": "Chaveiro",
        "categoria": "Acessórios",
        "data_ocorrencia": date(2026, 5, 10),
        "local_ocorrencia": "Bloco Vermelho",
        "foto_referencia": "fotos/chaveiro.png",
    })
    nucleo.confirmar(lote1)

    lote2 = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.ENCONTRADO,
        "nome": "Guarda-chuva",
        "categoria": "Utilidades",
        "data_ocorrencia": date(2026, 5, 12),
        "local_ocorrencia": "Entrada",
        "foto_referencia": "fotos/guarda-chuva.png",
        "situacao_guarda": SituacaoGuarda.EM_SETOR,
        "setor_guarda": "Recepção",
    })
    nucleo.confirmar(lote2)

    assert len(lista) == 2
    assert len(indice) == 2

    # 2. Simula o reinício do sistema criando novas estruturas em memória
    novo_repo = RepositorioOcorrenciasJSON(caminho)
    nova_lista = ListaDinamica()
    novo_indice = ArvoreAVL()

    inicializar_ocorrencias(novo_repo, nova_lista, novo_indice)

    assert len(nova_lista) == 2
    assert len(novo_indice) == 2

    itens_recarregados = list(nova_lista)
    nomes = {item.nome for item in itens_recarregados}
    assert "Chaveiro" in nomes
    assert "Guarda-chuva" in nomes

    # Verifica se a AVL recuperou os IDs no período
    ids_periodo = list(novo_indice.buscar_periodo(date(2026, 5, 1), date(2026, 5, 31)))
    assert len(ids_periodo) == 2


def test_datas_iguais_na_avl(ambiente):
    repo, lista, indice, armazenamento, nucleo, consulta, _ = ambiente
    mesma_data = date(2026, 6, 15)

    for i in range(3):
        lote = nucleo.preparar_cadastro({
            "tipo": TipoOcorrencia.PERDIDO,
            "nome": f"Objeto {i}",
            "categoria": "Diversos",
            "data_ocorrencia": mesma_data,
            "local_ocorrencia": f"Sala {i}",
            "foto_referencia": f"fotos/obj_{i}.png",
        })
        nucleo.confirmar(lote)

    assert len(lista) == 3
    assert len(indice) == 3

    # A busca por período na AVL deve retornar todos os 3 registros
    ids = list(indice.buscar_periodo(mesma_data, mesma_data))
    assert len(ids) == 3

    resultados = consulta.buscar_periodo(mesma_data, mesma_data)
    assert len(resultados) == 3


def test_alteracao_de_data_sem_indice_antigo(ambiente):
    repo, lista, indice, armazenamento, nucleo, consulta, _ = ambiente
    data_antiga = date(2026, 4, 1)
    data_nova = date(2026, 4, 20)

    lote_cad = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.PERDIDO,
        "nome": "Casaco",
        "categoria": "Vestuário",
        "data_ocorrencia": data_antiga,
        "local_ocorrencia": "Cantina",
        "foto_referencia": "fotos/casaco.png",
    })
    nucleo.confirmar(lote_cad)
    oc_id = lote_cad.alteracoes[0].posterior.id

    # Verifica que está na data antiga
    assert list(indice.buscar_periodo(data_antiga, data_antiga)) == [oc_id]
    assert list(indice.buscar_periodo(data_nova, data_nova)) == []

    # Edita a data de ocorrência
    lote_edit = nucleo.preparar_edicao(oc_id, {"data_ocorrencia": data_nova})
    nucleo.confirmar(lote_edit)

    # O índice antigo NÃO deve mais conter o ID
    assert list(indice.buscar_periodo(data_antiga, data_antiga)) == []
    # O novo índice deve conter o ID
    assert list(indice.buscar_periodo(data_nova, data_nova)) == [oc_id]

    # Verifica no JSON que a data foi atualizada
    recarregado = repo.carregar()
    assert recarregado[0].data_ocorrencia == data_nova


def test_exclusao_e_limpeza_de_vinculos(ambiente):
    repo, lista, indice, armazenamento, nucleo, consulta, _ = ambiente

    lote_p = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.PERDIDO,
        "nome": "Carteira",
        "categoria": "Documentos",
        "data_ocorrencia": date(2026, 3, 1),
        "local_ocorrencia": "Auditório",
        "foto_referencia": "fotos/carteira.png",
    })
    nucleo.confirmar(lote_p)
    p_id = lote_p.alteracoes[0].posterior.id

    lote_e = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.ENCONTRADO,
        "nome": "Carteira Encontrada",
        "categoria": "Documentos",
        "data_ocorrencia": date(2026, 3, 2),
        "local_ocorrencia": "Auditório",
        "foto_referencia": "fotos/carteira_achada.png",
        "situacao_guarda": SituacaoGuarda.EM_SETOR,
        "setor_guarda": "Secretaria",
    })
    nucleo.confirmar(lote_e)
    e_id = lote_e.alteracoes[0].posterior.id

    # Vincula as ocorrências
    lote_vinc = nucleo.preparar_vinculo(p_id, e_id)
    nucleo.confirmar(lote_vinc)

    assert nucleo.obter(p_id).vinculo_id == e_id
    assert nucleo.obter(e_id).vinculo_id == p_id

    # Exclui a ocorrência de perda
    lote_exc = nucleo.preparar_exclusao(p_id)
    nucleo.confirmar(lote_exc)

    # p_id foi excluído fisicamente
    assert armazenamento.obter(p_id) is None
    assert len(lista) == 1
    assert list(indice.buscar_periodo(date(2026, 3, 1), date(2026, 3, 1))) == []

    # O parceiro e_id foi preservado, mas seu vínculo foi limpo
    parceiro = nucleo.obter(e_id)
    assert parceiro.vinculo_id is None

    # Verifica também no arquivo JSON
    registros_json = repo.carregar()
    assert len(registros_json) == 1
    assert registros_json[0].id == e_id
    assert registros_json[0].vinculo_id is None


def test_resolucao_e_reabertura_dos_dois_registros(ambiente):
    repo, lista, indice, armazenamento, nucleo, consulta, _ = ambiente

    lote_p = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.PERDIDO,
        "nome": "Celular",
        "categoria": "Eletrônicos",
        "data_ocorrencia": date(2026, 2, 1),
        "local_ocorrencia": "Lab 1",
        "foto_referencia": "fotos/celular.png",
    })
    nucleo.confirmar(lote_p)
    p_id = lote_p.alteracoes[0].posterior.id

    lote_e = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.ENCONTRADO,
        "nome": "Celular Achado",
        "categoria": "Eletrônicos",
        "data_ocorrencia": date(2026, 2, 1),
        "local_ocorrencia": "Lab 1",
        "foto_referencia": "fotos/celular_achado.png",
        "situacao_guarda": SituacaoGuarda.EM_SETOR,
        "setor_guarda": "TI",
    })
    nucleo.confirmar(lote_e)
    e_id = lote_e.alteracoes[0].posterior.id

    nucleo.confirmar(nucleo.preparar_vinculo(p_id, e_id))

    # Resolução (ambos passam a RESOLVIDO)
    lote_res = nucleo.preparar_resolucao(p_id)
    nucleo.confirmar(lote_res)

    assert nucleo.obter(p_id).status is StatusOcorrencia.RESOLVIDO
    assert nucleo.obter(e_id).status is StatusOcorrencia.RESOLVIDO

    # Verifica no JSON
    itens_json = {i.id: i.status for i in repo.carregar()}
    assert itens_json[p_id] is StatusOcorrencia.RESOLVIDO
    assert itens_json[e_id] is StatusOcorrencia.RESOLVIDO

    # Reabertura (ambos voltam para ABERTO)
    lote_reab = nucleo.preparar_reabertura(e_id)
    nucleo.confirmar(lote_reab)

    assert nucleo.obter(p_id).status is StatusOcorrencia.ABERTO
    assert nucleo.obter(e_id).status is StatusOcorrencia.ABERTO

    itens_json = {i.id: i.status for i in repo.carregar()}
    assert itens_json[p_id] is StatusOcorrencia.ABERTO
    assert itens_json[e_id] is StatusOcorrencia.ABERTO


def test_falha_de_gravacao_preserva_memoria(ambiente, monkeypatch):
    repo, lista, indice, armazenamento, nucleo, consulta, _ = ambiente

    lote1 = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.PERDIDO,
        "nome": "Item Base",
        "categoria": "Geral",
        "data_ocorrencia": date(2026, 1, 1),
        "local_ocorrencia": "Campus",
        "foto_referencia": "fotos/base.png",
    })
    nucleo.confirmar(lote1)
    base_id = lote1.alteracoes[0].posterior.id

    assert len(lista) == 1
    assert len(indice) == 1

    # Simula falha ao tentar salvar
    def simular_falha_salvar(ocorrencias):
        raise ErroPersistencia("Falha forçada de gravação em disco.")

    monkeypatch.setattr(repo, "salvar", simular_falha_salvar)

    lote2 = nucleo.preparar_cadastro({
        "tipo": TipoOcorrencia.ENCONTRADO,
        "nome": "Item Falha",
        "categoria": "Geral",
        "data_ocorrencia": date(2026, 1, 2),
        "local_ocorrencia": "Campus",
        "foto_referencia": "fotos/falha.png",
        "situacao_guarda": SituacaoGuarda.AINDA_NAO_ENTREGUE,
    })

    with pytest.raises(ErroPersistencia):
        nucleo.confirmar(lote2)

    # A memória (Lista e AVL) deve permanecer com apenas 1 item
    assert len(lista) == 1
    assert len(indice) == 1
    assert armazenamento.obter(base_id) is not None
    assert list(lista)[0].id == base_id


def test_compor_producao_integra_com_app_flask(tmp_path):
    caminho_contas = tmp_path / "contas.json"
    caminho_ocorrencias = tmp_path / "ocorrencias.json"
    caminho_fotos = tmp_path / "fotos"

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-secreta-de-teste",
        "CONTAS_HABILITADAS": True,
        "OCORRENCIAS_HABILITADAS": True,
        "CONTAS_JSON": caminho_contas,
        "OCORRENCIAS_JSON": caminho_ocorrencias,
        "FOTOS_DIRETORIO": caminho_fotos,
        "OCORRENCIAS_COMPOSITOR": "app.services.inicializacao:compor_producao",
    })

    # Prepara admin e secretário no repositório de contas
    app.extensions["autenticacao"].inicializar_administrador(
        {"nome": "Admin", "identificador": "admin@pucpr.edu.br"},
        "Senha-Segura-123!",
    )

    client = app.test_client()

    # O endpoint público /ocorrencias deve responder com 200 usando as estruturas reais
    resposta = client.get("/ocorrencias")
    assert resposta.status_code == 200
    assert "Nenhuma ocorrência encontrada" in resposta.get_data(as_text=True)

    # Verifica que o arquivo de ocorrências foi inicializado
    assert caminho_ocorrencias.exists()

