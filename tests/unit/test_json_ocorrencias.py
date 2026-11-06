"""Testes de unidade da persistência JSON de ocorrências (Matheus)."""

from datetime import date
import json
from pathlib import Path

import pytest

from app.erros import ErroPersistencia, ErroValidacao
from app.models.ocorrencia import Ocorrencia, SituacaoGuarda, StatusOcorrencia, TipoOcorrencia
from app.repositories.json_contas import RepositorioContasJSON
from app.repositories.json_ocorrencias import RepositorioOcorrenciasJSON


def ocorrencia_exemplo(
    id="oc-1",
    tipo=TipoOcorrencia.PERDIDO,
    data=date(2026, 10, 1),
    foto="fotos/teste1.png",
    **extra,
) -> Ocorrencia:
    dados = {
        "id": id,
        "tipo": tipo,
        "nome": "Caderno",
        "categoria": "Material escolar",
        "data_ocorrencia": data,
        "local_ocorrencia": "Biblioteca",
        "foto_referencia": foto,
        "descricao": "Caderno azul",
        "cor": "Azul",
        "status": StatusOcorrencia.ABERTO,
        **extra,
    }
    return Ocorrencia(**dados)


def test_construtor_e_consulta_nao_criam_dados(tmp_path):
    caminho = tmp_path / "nao-criado" / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)
    assert not caminho.parent.exists()
    with pytest.raises(ErroPersistencia):
        repo.carregar()
    assert not caminho.parent.exists()


def test_inicializar_cria_arquivo_vazio_com_versao(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)
    repo.inicializar()
    assert caminho.exists()
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados == {"versao": 1, "ocorrencias": []}


def test_inicializar_arquivo_existente_valida_sem_apagar(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)
    item = ocorrencia_exemplo()
    repo.salvar([item])

    reaberto = RepositorioOcorrenciasJSON(caminho)
    reaberto.inicializar()
    carregados = reaberto.carregar()
    assert len(carregados) == 1
    assert carregados[0].id == item.id


def test_salvar_e_carregar_completo_com_todos_os_campos(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)

    perdido = ocorrencia_exemplo(
        id="oc-p",
        tipo=TipoOcorrencia.PERDIDO,
        data=date(2026, 10, 5),
        foto="fotos/perdido.png",
        vinculo_id="oc-e",
    )
    encontrado = Ocorrencia(
        id="oc-e",
        tipo=TipoOcorrencia.ENCONTRADO,
        nome="Relógio",
        categoria="Acessórios",
        data_ocorrencia=date(2026, 10, 6),
        local_ocorrencia="Pátio",
        foto_referencia="fotos/encontrado.png",
        descricao="Relógio prata",
        cor="Prata",
        status=StatusOcorrencia.ABERTO,
        situacao_guarda=SituacaoGuarda.EM_SETOR,
        setor_guarda="Bloco 2",
        data_recebimento=date(2026, 10, 7),
        destinacao_a_verificar=True,
        vinculo_id="oc-p",
    )

    repo.salvar([perdido, encontrado])

    reaberto = RepositorioOcorrenciasJSON(caminho)
    itens = reaberto.carregar()
    assert len(itens) == 2

    p = next(i for i in itens if i.id == "oc-p")
    e = next(i for i in itens if i.id == "oc-e")

    assert p.tipo == TipoOcorrencia.PERDIDO
    assert p.data_ocorrencia == date(2026, 10, 5)
    assert p.foto_referencia == "fotos/perdido.png"
    assert p.vinculo_id == "oc-e"

    assert e.tipo == TipoOcorrencia.ENCONTRADO
    assert e.data_ocorrencia == date(2026, 10, 6)
    assert e.situacao_guarda == SituacaoGuarda.EM_SETOR
    assert e.setor_guarda == "Bloco 2"
    assert e.data_recebimento == date(2026, 10, 7)
    assert e.destinacao_a_verificar is True
    assert e.vinculo_id == "oc-p"


def test_fotos_obrigatorias_rejeita_vazio_ou_invalido(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)

    with pytest.raises(ErroValidacao):
        ocorrencia_exemplo(foto="")

    with pytest.raises(ErroValidacao):
        ocorrencia_exemplo(foto="../escape.png")

    with pytest.raises(ErroValidacao):
        ocorrencia_exemplo(foto="C:\\absoluto.png")


def test_falha_de_gravacao_preserva_arquivo_existente(tmp_path, monkeypatch):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)
    item_original = ocorrencia_exemplo(id="original")
    repo.salvar([item_original])

    def simular_falha_replace(src, dst):
        raise OSError("Falha simulada durante substituição de arquivo.")

    monkeypatch.setattr("os.replace", simular_falha_replace)

    item_novo = ocorrencia_exemplo(id="novo")
    with pytest.raises(ErroPersistencia):
        repo.salvar([item_novo])

    # O arquivo original deve permanecer íntegro
    monkeypatch.undo()
    carregados = repo.carregar()
    assert len(carregados) == 1
    assert carregados[0].id == "original"


def test_arquivo_json_invalido_ou_corrompido_lanca_erro(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    caminho.write_text("{conteúdo json corrompido", encoding="utf-8")
    repo = RepositorioOcorrenciasJSON(caminho)
    with pytest.raises(ErroPersistencia):
        repo.carregar()

    # Não deve sobrescrever o arquivo corrompido ao tentar inicializar
    with pytest.raises(ErroPersistencia):
        repo.inicializar()
    assert caminho.read_text(encoding="utf-8") == "{conteúdo json corrompido"


def test_versao_incompativel_lanca_erro(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    caminho.write_text(json.dumps({"versao": 99, "ocorrencias": []}), encoding="utf-8")
    repo = RepositorioOcorrenciasJSON(caminho)
    with pytest.raises(ErroPersistencia, match="incompatível"):
        repo.carregar()


def test_ids_duplicados_ou_vinculos_inconsistentes_no_json(tmp_path):
    caminho = tmp_path / "ocorrencias.json"
    repo = RepositorioOcorrenciasJSON(caminho)

    item = ocorrencia_exemplo(id="mesmo-id")
    registro = item.para_registro()

    # JSON com IDs duplicados
    caminho.write_text(
        json.dumps({"versao": 1, "ocorrencias": [registro, registro]}),
        encoding="utf-8",
    )
    with pytest.raises(ErroPersistencia, match="duplicados|inconsistentes"):
        repo.carregar()

    # JSON com vínculo fantasma
    registro_vinculo_fantasma = {**registro, "vinculo_id": "id-inexistente"}
    caminho.write_text(
        json.dumps({"versao": 1, "ocorrencias": [registro_vinculo_fantasma]}),
        encoding="utf-8",
    )
    with pytest.raises(ErroPersistencia, match="inconsistente"):
        repo.carregar()


def test_contas_administrativas_preservadas_separadamente(tmp_path):
    caminho_contas = tmp_path / "contas.json"
    caminho_ocorrencias = tmp_path / "ocorrencias.json"

    repo_contas = RepositorioContasJSON(caminho_contas)
    repo_contas.inicializar()
    repo_contas.inicializar_administrador(
        {"nome": "Admin", "identificador": "admin@pucpr.edu.br"},
        senha_hash="hash123",
    )

    repo_ocorrencias = RepositorioOcorrenciasJSON(caminho_ocorrencias)
    repo_ocorrencias.inicializar()
    item = ocorrencia_exemplo(id="oc-sep")
    repo_ocorrencias.salvar([item])

    assert caminho_contas.exists()
    assert caminho_ocorrencias.exists()

    contas = repo_contas.buscar_por_identificador("admin@pucpr.edu.br")
    assert contas is not None
    assert contas.nome == "Admin"

    ocorrencias = repo_ocorrencias.carregar()
    assert len(ocorrencias) == 1
    assert ocorrencias[0].id == "oc-sep"

