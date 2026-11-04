"""Validação de bytes, isolamento de caminhos e leitura de fotos em tmp_path."""

from io import BytesIO

from PIL import Image
import pytest

from app.erros import ErroPersistencia, ErroValidacao
from app.repositories.fotos import FotosLocais


def imagem(formato="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (12, 8), "blue").save(buffer, format=formato)
    return buffer.getvalue()


@pytest.mark.parametrize("formato,tipo", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_foto_real_e_recuperada_sem_nome_original(tmp_path, formato, tipo):
    pasta = tmp_path / "fotos"
    fotos = FotosLocais(pasta, limite_bytes=1_500_000, formatos=("JPEG", "PNG"))
    assert not pasta.exists()
    conteudo = imagem(formato)
    referencia = fotos.salvar(BytesIO(conteudo))
    assert referencia.startswith("ocorrencias/")
    foto = fotos.ler(referencia)
    assert foto.conteudo == conteudo
    assert foto.tipo_mime == tipo
    fotos.remover(referencia)
    with pytest.raises(ErroPersistencia):
        fotos.ler(referencia)


@pytest.mark.parametrize("conteudo", [b"", b"<html>arquivo falso</html>", b"\x89PNG\r\n\x1a\ntruncado"])
def test_arquivo_invalido_nao_cria_diretorios(tmp_path, conteudo):
    pasta = tmp_path / "fotos"
    fotos = FotosLocais(pasta, limite_bytes=1000, formatos=("JPEG", "PNG"))
    with pytest.raises(ErroValidacao):
        fotos.salvar(BytesIO(conteudo))
    assert not pasta.exists()


def test_limite_real_de_bytes_e_formato_restrito(tmp_path):
    fotos = FotosLocais(tmp_path, limite_bytes=50, formatos=("JPEG", "PNG"))
    with pytest.raises(ErroValidacao):
        fotos.salvar(BytesIO(imagem()))
    fotos = FotosLocais(tmp_path, limite_bytes=1000, formatos=("JPEG",))
    with pytest.raises(ErroValidacao):
        fotos.salvar(BytesIO(imagem("PNG")))


@pytest.mark.parametrize("referencia", ["../fora.png", "/tmp/fora.png", "a/../fora.png", "a\\fora.png", "a//fora.png"])
def test_caminhos_externos_sao_recusados(tmp_path, referencia):
    fotos = FotosLocais(tmp_path, limite_bytes=1000, formatos=("PNG",))
    with pytest.raises(ErroPersistencia):
        fotos.ler(referencia)


def test_link_simbolico_nao_permite_ler_fora_da_raiz(tmp_path):
    pasta, fora = tmp_path / "fotos", tmp_path / "fora"
    pasta.mkdir()
    fora.mkdir()
    (fora / "imagem.png").write_bytes(imagem())
    (pasta / "atalho").symlink_to(fora, target_is_directory=True)
    fotos = FotosLocais(pasta, limite_bytes=1000, formatos=("PNG",))
    with pytest.raises(ErroPersistencia):
        fotos.ler("atalho/imagem.png")
