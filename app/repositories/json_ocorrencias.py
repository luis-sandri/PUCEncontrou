"""Repositório JSON local de ocorrências; não conhece estruturas em memória."""

from collections.abc import Iterable
import json
import os
from pathlib import Path
import tempfile
from threading import RLock

from app.erros import ErroPersistencia, ErroValidacao
from app.models.alteracao_ocorrencias import validar_estado_ocorrencias
from app.models.ocorrencia import Ocorrencia


class RepositorioOcorrenciasJSON:
    """Persiste snapshots versionados, sem criar arquivos no construtor."""

    def __init__(self, caminho: Path | str) -> None:
        self.caminho = Path(caminho)
        self._lock = RLock()

    def carregar(self) -> tuple[Ocorrencia, ...]:
        with self._lock:
            try:
                with self.caminho.open(encoding="utf-8") as arquivo:
                    documento = json.load(arquivo)
            except (OSError, UnicodeError, ValueError):
                raise ErroPersistencia("Não foi possível ler o arquivo de ocorrências.") from None
            if (not isinstance(documento, dict) or set(documento) != {"versao", "ocorrencias"}
                    or type(documento["versao"]) is not int or documento["versao"] != 1
                    or not isinstance(documento["ocorrencias"], list)):
                raise ErroPersistencia("Versão ou formato do arquivo de ocorrências incompatível.")
            try:
                estado = tuple(Ocorrencia.de_registro(registro) for registro in documento["ocorrencias"])
                validar_estado_ocorrencias(estado)
            except (ErroValidacao, TypeError):
                raise ErroPersistencia("Arquivo de ocorrências contém registros inválidos.") from None
            return estado

    def salvar(self, ocorrencias: Iterable[Ocorrencia]) -> None:
        with self._lock:
            try:
                estado = tuple(ocorrencias)
                validar_estado_ocorrencias(estado)
                registros = []
                for item in estado:
                    if not isinstance(item, Ocorrencia):
                        raise ErroValidacao("O repositório exige ocorrências validadas.")
                    registros.append(item.para_registro())
            except (ErroValidacao, TypeError):
                raise ErroValidacao("Snapshot de ocorrências inválido.") from None

            temporario = None
            try:
                self.caminho.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.caminho.parent,
                    prefix=".ocorrencias-",
                    suffix=".tmp",
                    delete=False,
                ) as arquivo:
                    temporario = Path(arquivo.name)
                    json.dump(
                        {"versao": 1, "ocorrencias": registros},
                        arquivo,
                        ensure_ascii=False,
                        indent=2,
                    )
                    arquivo.write("\n")
                    arquivo.flush()
                    os.fsync(arquivo.fileno())
                os.replace(temporario, self.caminho)
            except (OSError, UnicodeError, ValueError):
                raise ErroPersistencia("Não foi possível salvar o arquivo de ocorrências.") from None
            finally:
                if temporario is not None:
                    try:
                        temporario.unlink(missing_ok=True)
                    except OSError:
                        pass

    def inicializar(self) -> None:
        """Cria um snapshot vazio explicitamente ou valida o arquivo existente."""
        with self._lock:
            if self.caminho.exists():
                self.carregar()
            else:
                self.salvar(())
