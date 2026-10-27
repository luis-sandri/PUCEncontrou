"""Demonstração de estudo: execute python -m tests.exemplo_scrum8 na raiz.

O armazenamento abaixo é fake e não pode substituir a Lista manual na aplicação.
"""

import json
from collections.abc import Iterable
from datetime import date

from app.erros import OcorrenciaNaoEncontrada
from app.models.alteracao_ocorrencias import LoteOcorrencias
from app.models.ocorrencia import Ocorrencia, StatusOcorrencia
from app.services.nucleo_ocorrencias import NucleoOcorrencias


class ArmazenamentoDemonstracao:
    """Fake isolado: não persiste e não oferece concorrência de produção."""

    def __init__(self) -> None:
        self._registros: tuple[Ocorrencia, ...] = ()

    def obter(self, ocorrencia_id: str) -> Ocorrencia | None:
        return next((item for item in self._registros if item.id == ocorrencia_id), None)

    def listar(self) -> Iterable[Ocorrencia]:
        return iter(self._registros)

    def aplicar(self, lote: LoteOcorrencias) -> None:
        self._registros = lote.preparar_estado(self._registros)


def main() -> None:
    nucleo = NucleoOcorrencias(ArmazenamentoDemonstracao())
    dados = {
        "tipo": "PERDIDO", "nome": "Garrafa azul", "categoria": "Garrafas",
        "data_ocorrencia": date(2026, 10, 19), "local_ocorrencia": "Biblioteca",
        "foto_referencia": "ocorrencias/garrafa-perdida.jpg",
    }
    cadastro = nucleo.preparar_cadastro(dados)
    perdido_id = cadastro.alteracoes[0].id
    assert nucleo.listar() == ()  # Preparar não publica.
    nucleo.confirmar(cadastro)

    cadastro_achado = nucleo.preparar_cadastro({
        **dados, "tipo": "ENCONTRADO", "foto_referencia": "ocorrencias/garrafa-achada.jpg",
        "situacao_guarda": "EM_SETOR", "setor_guarda": "Bloco 9",
        "data_recebimento": date(2026, 10, 21),
    })
    encontrado_id = cadastro_achado.alteracoes[0].id
    nucleo.confirmar(cadastro_achado)
    nucleo.confirmar(nucleo.preparar_vinculo(perdido_id, encontrado_id))
    nucleo.confirmar(nucleo.preparar_resolucao(perdido_id))
    assert all(item.status is StatusOcorrencia.RESOLVIDO for item in nucleo.listar())

    # Demonstra codec JSON sem acessar arquivo ou implementar o repositório.
    registro = nucleo.obter(encontrado_id).para_registro()
    assert Ocorrencia.de_registro(json.loads(json.dumps(registro))) == nucleo.obter(encontrado_id)
    print("Devolucao: os dois registros foram resolvidos.")
    nucleo.confirmar(nucleo.preparar_reabertura(encontrado_id))
    assert all(item.status is StatusOcorrencia.ABERTO for item in nucleo.listar())
    nucleo.preparar_exclusao(encontrado_id)  # Desistência: não confirmar.
    assert len(nucleo.listar()) == 2
    nucleo.confirmar(nucleo.preparar_exclusao(perdido_id))
    try:
        nucleo.obter(perdido_id)
    except OcorrenciaNaoEncontrada:
        pass
    else:
        raise AssertionError("O registro deveria ter sido excluído.")
    assert nucleo.obter(encontrado_id).vinculo_id is None
    assert nucleo.obter(encontrado_id).data_recebimento == date(2026, 10, 21)
    print("Reabertura e exclusao: parceiro preservado, sem vinculo orfao.")
    print("Demonstracao concluida com fake; nenhum arquivo de dados foi criado.")


if __name__ == "__main__":
    main()
