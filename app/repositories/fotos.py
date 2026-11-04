"""Uploads de Luís: valida bytes e guarda fotos fora dos arquivos estáticos."""

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import uuid4
from contextlib import suppress
import warnings

from PIL import Image, UnidentifiedImageError

from app.erros import ErroPersistencia, ErroValidacao


@dataclass(frozen=True)
class FotoPublica:
    conteudo: bytes
    tipo_mime: str


class RepositorioFotosPorta(Protocol):
    def salvar(self, arquivo: BinaryIO) -> str: ...
    def ler(self, referencia: str) -> FotoPublica: ...
    def remover(self, referencia: str) -> None: ...


class FotosLocais:
    """Construtor sem I/O. Nome aleatório gerado a partir do formato real."""

    def __init__(self, diretorio: Path | str, *, limite_bytes: int, formatos: Iterable[str]) -> None:
        if type(limite_bytes) is not int or limite_bytes <= 0:
            raise ValueError("Defina um limite positivo para fotos.")
        if formatos is None:
            raise ValueError("Defina os formatos de foto permitidos.")
        formatos = frozenset(formatos)
        if not formatos or not formatos <= {"JPEG", "PNG"}:
            raise ValueError("Defina os formatos de foto permitidos: JPEG e/ou PNG.")
        self._diretorio = Path(diretorio)
        self.limite_bytes = limite_bytes
        self.formatos = formatos

    def _validar(self, conteudo: bytes) -> str:
        if not conteudo or len(conteudo) > self.limite_bytes:
            raise ErroValidacao("Envie uma foto dentro do limite de tamanho informado.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(conteudo), formats=list(self.formatos)) as imagem:
                    formato = imagem.format
                    imagem.verify()
                with Image.open(BytesIO(conteudo), formats=list(self.formatos)) as imagem:
                    imagem.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ErroValidacao("Envie uma imagem válida em um dos formatos permitidos.") from None
        return formato

    def _caminho(self, referencia: str) -> Path:
        if not isinstance(referencia, str) or any(c in referencia for c in "\\:?#"):
            raise ErroPersistencia("Referência de foto inválida.")
        partes = referencia.split("/")
        if (PurePosixPath(referencia).is_absolute()
                or any(parte in {"", ".", ".."} for parte in partes)):
            raise ErroPersistencia("Referência de foto inválida.")
        raiz = self._diretorio.resolve()
        caminho = (raiz / referencia).resolve()
        if not caminho.is_relative_to(raiz):
            raise ErroPersistencia("Referência de foto inválida.")
        return caminho

    def salvar(self, arquivo: BinaryIO) -> str:
        conteudo = arquivo.read(self.limite_bytes + 1)
        formato = self._validar(conteudo)
        extensao = "jpg" if formato == "JPEG" else "png"
        referencia = f"ocorrencias/{uuid4().hex}.{extensao}"
        caminho = self._caminho(referencia)
        criado = False
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with caminho.open("xb") as destino:
                criado = True
                destino.write(conteudo)
        except OSError:
            if criado:
                with suppress(OSError):
                    caminho.unlink(missing_ok=True)
            raise ErroPersistencia("Não foi possível salvar a foto.") from None
        return referencia

    def ler(self, referencia: str) -> FotoPublica:
        caminho = self._caminho(referencia)
        try:
            with caminho.open("rb") as arquivo:
                conteudo = arquivo.read(self.limite_bytes + 1)
            formato = self._validar(conteudo)
        except (OSError, ErroValidacao):
            raise ErroPersistencia("Foto indisponível.") from None
        return FotoPublica(conteudo, "image/jpeg" if formato == "JPEG" else "image/png")

    def remover(self, referencia: str) -> None:
        try:
            self._caminho(referencia).unlink(missing_ok=True)
        except OSError:
            raise ErroPersistencia("Não foi possível descartar a foto não utilizada.") from None
