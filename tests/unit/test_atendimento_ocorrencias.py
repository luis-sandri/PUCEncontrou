"""Serviço de Luís testado com portas fake; domínio real pertence a Marcelo."""

from dataclasses import replace
from datetime import date
from io import BytesIO

from PIL import Image
import pytest

from app.erros import ErroPersistencia, ErroValidacao, PermissaoNegada
from app.models.conta import Perfil
from app.models.ocorrencia import StatusOcorrencia
from app.repositories.json_contas import RepositorioContasJSON
from app.services.atendimento_ocorrencias import AtendimentoOcorrencias
from app.services.autenticacao import ServicoAutenticacao
from app.services.contas import ServicoContas
from app.repositories.fotos import FotosLocais
from tests.fakes_ocorrencias import ConsultaFake, criar_nucleo

SENHA = "Senha-ficticia-123!"


def imagem():
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def dados(**extra):
    return {"tipo": "PERDIDO", "nome": "Garrafa fictícia", "categoria": "Teste",
            "data_ocorrencia": "2026-10-01", "local_ocorrencia": "Local fictício", **extra}


@pytest.fixture
def contexto(tmp_path):
    repo = RepositorioContasJSON(tmp_path / "contas.json")
    auth = ServicoAutenticacao(repo)
    admin = auth.inicializar_administrador({"nome": "Admin fictício", "identificador": "admin@pucpr.edu.br"}, SENHA)
    gestao = ServicoContas(repo)
    secretario = gestao.cadastrar_secretario({"nome": "Secretário fictício", "identificador": "secretario@pucpr.edu.br"}, SENHA, ator=admin)
    nucleo = criar_nucleo()
    consulta = ConsultaFake(nucleo)
    fotos = FotosLocais(tmp_path / "fotos", limite_bytes=1_500_000, formatos=("JPEG", "PNG"))
    servico = AtendimentoOcorrencias(nucleo, consulta, repo, fotos, setor_publico=True, cancelamento_habilitado=True)
    return servico, nucleo, consulta, gestao, admin, secretario, tmp_path


def test_cadastro_data_foto_e_visao_explicita(contexto):
    servico, _, _, _, _, _, pasta = contexto
    item = servico.cadastrar(dados(), foto=imagem())
    assert item.data_ocorrencia == date(2026, 10, 1)
    visao = servico.visao(item)
    assert "foto_referencia" not in visao
    assert "vinculo_id" not in visao
    assert "data_recebimento" not in visao
    assert str(pasta) not in str(visao)
    assert servico.foto_publica(item.id).tipo_mime == "image/png"


@pytest.mark.parametrize("alteracao", [{"status": "RESOLVIDO"}, {"id": "forjado"}, {"foto_referencia": "fora.png"}, {"ator": "admin"}, {"destinacao_a_verificar": True}])
def test_cadastro_rejeita_campos_controlados(contexto, alteracao):
    servico, nucleo, _, _, _, _, pasta = contexto
    with pytest.raises(ErroValidacao):
        servico.cadastrar(dados(**alteracao), foto=imagem())
    assert tuple(nucleo.listar()) == ()
    assert not (pasta / "fotos").exists()


@pytest.mark.parametrize("ator_indice", [None, "admin", "forjado"])
def test_mutacoes_exigem_secretario_real(contexto, ator_indice):
    servico, _, _, _, admin, secretario, _ = contexto
    item = servico.cadastrar(dados(), foto=imagem())
    ator = {None: None, "admin": admin, "forjado": replace(admin, perfil=Perfil.SECRETARIO)}[ator_indice]
    for operacao in (
        lambda: servico.editar(item.id, {"nome": "Outro"}, ator=ator),
        lambda: servico.excluir(item.id, ator=ator, confirmacao=True),
        lambda: servico.alterar_status(item.id, StatusOcorrencia.CANCELADO, ator=ator, contexto={}),
        lambda: servico.vincular(item.id, "outro", ator=ator),
    ):
        with pytest.raises(PermissaoNegada):
            operacao()
    assert servico.obter(item.id).nome == item.nome


def test_ator_com_sessao_revogada_e_recusado(contexto):
    servico, _, _, gestao, admin, secretario, _ = contexto
    item = servico.cadastrar(dados(), foto=imagem())
    gestao.gerenciar_secretario(secretario.id, {"senha": "Outra-senha-123!"}, ator=admin)
    with pytest.raises(PermissaoNegada):
        servico.editar(item.id, {"nome": "Outro"}, ator=secretario)


def test_falha_de_confirmacao_descarta_somente_foto_nova(contexto, monkeypatch):
    servico, nucleo, _, _, _, secretario, pasta = contexto
    item = servico.cadastrar(dados(), foto=imagem())
    antes = set((pasta / "fotos").rglob("*.png"))
    def falhar(lote):
        raise ErroPersistencia("Falha fictícia")
    monkeypatch.setattr(nucleo, "confirmar", falhar)
    with pytest.raises(ErroPersistencia):
        servico.editar(item.id, {"nome": "Outro"}, ator=secretario, foto=imagem())
    assert set((pasta / "fotos").rglob("*.png")) == antes
    assert servico.obter(item.id) == item


def test_consulta_temporal_e_delegada_e_filtra_resultados(contexto):
    servico, _, consulta, _, _, _, _ = contexto
    a = servico.cadastrar(dados(nome="Garrafa", data_ocorrencia="2026-10-01"), foto=imagem())
    servico.cadastrar(dados(nome="Caderno", data_ocorrencia="2026-10-02"), foto=imagem())
    resultado = servico.listar({"inicio": "2026-10-01", "fim": "2026-10-02", "q": "garrafa", "tipo": "PERDIDO"})
    assert [item.id for item in resultado] == [a.id]
    assert consulta.chamadas == [(date(2026, 10, 1), date(2026, 10, 2))]


@pytest.mark.parametrize("filtros", [{"inicio": "2026-10-02"}, {"inicio": "2026-10-02", "fim": "2026-10-01"}, {"tipo": "OUTRO"}, {"status": "OUTRO"}, {"extra": "campo"}, []])
def test_filtros_invalidos_sao_recusados(contexto, filtros):
    with pytest.raises(ErroValidacao):
        contexto[0].listar(filtros)


def test_devolucao_exige_confirmacao_e_vinculo_nao_resolve(contexto):
    servico, _, _, _, _, secretario, _ = contexto
    a = servico.cadastrar(dados(), foto=imagem())
    b = servico.cadastrar(dados(tipo="ENCONTRADO"), foto=imagem())
    assert all(item.status is StatusOcorrencia.ABERTO for item in servico.vincular(a.id, b.id, ator=secretario))
    with pytest.raises(ErroValidacao):
        servico.alterar_status(a.id, StatusOcorrencia.RESOLVIDO, ator=secretario, contexto={})
    alterados = servico.alterar_status(a.id, StatusOcorrencia.RESOLVIDO, ator=secretario, contexto={"confirmacao_presencial": True})
    assert {item.id for item in alterados} == {a.id, b.id}
    assert all(item.status is StatusOcorrencia.RESOLVIDO for item in alterados)
