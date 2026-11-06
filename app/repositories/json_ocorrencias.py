"""Persistência de ocorrências em JSON local com gravação atômica.

Responsabilidade de Matheus (SCRUM-13). Não expõe nós, estruturas ou arquivos ao frontend.
"""

from collections.abc import Iterable
from contextlib import suppress
import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from typing import Protocol

from app.erros import ErroPersistencia, ErroValidacao
from app.models.alteracao_ocorrencias import validar_estado_ocorrencias
from app.models.ocorrencia import Ocorrencia, OcorrenciaPorta


class RepositorioOcorrenciasPorta(Protocol):
    def carregar(self) -> Iterable[OcorrenciaPorta]: ...

    def salvar(self, ocorrencias: Iterable[OcorrenciaPorta]) -> None: ...


class RepositorioOcorrenciasJSON:
    """Repositório concreto de ocorrências persistidas em arquivo JSON local.

    Usa gravação atômica via arquivo temporário e os.replace no mesmo diretório.
    Não substitui arquivos corrompidos ou inválidos por listas vazias.
    O lock coordena operações concorrentes na mesma instância.
    """

    VERSAO_ESQUEMA = 1

    def __init__(self, caminho: Path | str) -> None:
        self.caminho = Path(caminho)
        self._lock = RLock()

    def inicializar(self) -> None:
        """Cria o arquivo vazio se não existir; se existir, valida o conteúdo."""
        with self._lock:
            if self.caminho.exists():
                self.carregar()
                return
            try:
                self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError as erro:
                raise ErroPersistencia("Não foi possível preparar o diretório de ocorrências.") from erro
            self._gravar([])

    def carregar(self) -> list[Ocorrencia]:
        """Carrega e valida o snapshot de ocorrências a partir do arquivo JSON."""
        with self._lock:
            try:
                with self.caminho.open("r", encoding="utf-8") as arquivo:
                    documento = json.load(arquivo)
            except (OSError, UnicodeError, ValueError) as erro:
                raise ErroPersistencia("Não foi possível ler o arquivo de ocorrências.") from erro

            if (not isinstance(documento, dict) or set(documento) != {"versao", "ocorrencias"}
                    or type(documento["versao"]) is not int
                    or documento["versao"] != self.VERSAO_ESQUEMA
                    or not isinstance(documento["ocorrencias"], list)):
                raise ErroPersistencia("Versão ou formato do arquivo de ocorrências incompatível.")

            registros = documento["ocorrencias"]
            ocorrencias = []
            for registro in registros:
                if not isinstance(registro, dict):
                    raise ErroPersistencia("Registro de ocorrência inválido no arquivo JSON.")
                try:
                    ocorrencia = Ocorrencia.de_registro(registro)
                except ErroValidacao as erro:
                    raise ErroPersistencia(f"Dados inconsistentes no arquivo de ocorrências: {erro}") from erro
                ocorrencias.append(ocorrencia)

            try:
                validar_estado_ocorrencias(tuple(ocorrencias))
            except ErroValidacao as erro:
                raise ErroPersistencia(f"Estado de ocorrências no arquivo JSON é inválido: {erro}") from erro

            return ocorrencias

    def salvar(self, ocorrencias: Iterable[OcorrenciaPorta]) -> None:
        """Salva atomicamente o snapshot completo de ocorrências."""
        with self._lock:
            itens_convertidos: list[Ocorrencia] = []
            for item in ocorrencias:
                if isinstance(item, Ocorrencia):
                    itens_convertidos.append(item)
                elif hasattr(item, "para_registro"):
                    try:
                        itens_convertidos.append(Ocorrencia.de_registro(item.para_registro()))
                    except ErroValidacao as erro:
                        raise ErroPersistencia(f"Ocorrência inválida para persistência: {erro}") from erro
                else:
                    raise ErroPersistencia("Objeto não é uma ocorrência válida para persistência.")

            try:
                validar_estado_ocorrencias(tuple(itens_convertidos))
            except ErroValidacao as erro:
                raise ErroPersistencia(f"Estado inválido para persistência: {erro}") from erro

            registros = [item.para_registro() for item in itens_convertidos]
            self._gravar(registros)

    def _gravar(self, registros: list[dict[str, object]]) -> None:
        """Grava snapshot em arquivo temporário com flush e fsync antes do os.replace."""
        temporario: Path | None = None
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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
                    {"versao": self.VERSAO_ESQUEMA, "ocorrencias": registros},
                    arquivo,
                    ensure_ascii=False,
                    indent=2,
                )
                arquivo.write("\n")
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, self.caminho)
        except (OSError, UnicodeError, ValueError) as erro:
            raise ErroPersistencia("Não foi possível salvar o arquivo de ocorrências.") from erro
        finally:
            if temporario is not None:
                with suppress(OSError):
                    temporario.unlink(missing_ok=True)
