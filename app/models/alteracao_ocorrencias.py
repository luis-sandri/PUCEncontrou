"""Lotes imutáveis para a integração publicar alterações como uma operação."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.erros import ConflitoAlteracao, ErroValidacao
from app.models.ocorrencia import Ocorrencia, StatusOcorrencia


def validar_estado_ocorrencias(estado: tuple[Ocorrencia, ...]) -> None:
    """Valida um snapshot temporário, inclusive integridade dos vínculos."""
    ids = set()
    for item in estado:
        if not isinstance(item, Ocorrencia):
            raise ErroValidacao("O armazenamento deve fornecer ocorrências validadas.")
        if item.id in ids:
            raise ErroValidacao("O snapshot contém IDs duplicados.")
        ids.add(item.id)
    for item in estado:
        if item.vinculo_id is None:
            continue
        parceiro = next((outro for outro in estado if outro.id == item.vinculo_id), None)
        if (parceiro is None or parceiro.vinculo_id != item.id or parceiro.tipo is item.tipo
                or parceiro.status is not item.status or item.status is StatusOcorrencia.CANCELADO):
            raise ErroValidacao("Vínculo inconsistente: são necessários parceiros recíprocos de tipos opostos e mesmo estado.")


@dataclass(frozen=True, slots=True)
class AlteracaoOcorrencia:
    anterior: Ocorrencia | None
    posterior: Ocorrencia | None

    def __post_init__(self) -> None:
        if self.anterior is None and self.posterior is None:
            raise ErroValidacao("Uma alteração precisa de estado anterior ou posterior.")
        for item in (self.anterior, self.posterior):
            if item is not None and not isinstance(item, Ocorrencia):
                raise ErroValidacao("Uma alteração exige ocorrências validadas.")
        if self.anterior is not None and self.posterior is not None:
            if self.anterior.id != self.posterior.id or self.anterior.tipo is not self.posterior.tipo:
                raise ErroValidacao("Uma alteração deve preservar ID e tipo.")

    @property
    def id(self) -> str:
        item = self.anterior if self.anterior is not None else self.posterior
        return item.id


@dataclass(frozen=True, slots=True)
class LoteOcorrencias:
    alteracoes: tuple[AlteracaoOcorrencia, ...]

    def __post_init__(self) -> None:
        if type(self.alteracoes) is not tuple or not self.alteracoes:
            raise ErroValidacao("O lote exige uma tupla não vazia de alterações.")
        ids = set()
        for alteracao in self.alteracoes:
            if not isinstance(alteracao, AlteracaoOcorrencia):
                raise ErroValidacao("Item inválido no lote de alterações.")
            if alteracao.id in ids:
                raise ErroValidacao("O lote não pode alterar o mesmo ID duas vezes.")
            ids.add(alteracao.id)

    def preparar_estado(self, atuais: Iterable[Ocorrencia]) -> tuple[Ocorrencia, ...]:
        """Valida precondições e produz snapshot temporário sem modificar a origem.

        A integração SCRUM-13 deve chamar este método sob seu lock, antes de
        persistir e publicar o estado inteiro. A tupla não é a Lista de produção.
        Não há I/O nem garantia de persistência implementada por este método.
        """
        estado = tuple(atuais)
        validar_estado_ocorrencias(estado)
        for alteracao in self.alteracoes:
            atual = next((item for item in estado if item.id == alteracao.id), None)
            if atual != alteracao.anterior:
                raise ConflitoAlteracao("Ocorrência alterada ou removida; prepare a operação novamente.")

        # Coleções abaixo são snapshots transitórios, nunca o armazenamento.
        novo = []
        for item in estado:
            alteracao = next((a for a in self.alteracoes if a.id == item.id), None)
            if alteracao is None:
                novo.append(item)
            elif alteracao.posterior is not None:
                novo.append(alteracao.posterior)
        for alteracao in self.alteracoes:
            if alteracao.anterior is None:
                novo.append(alteracao.posterior)
        resultado = tuple(novo)
        validar_estado_ocorrencias(resultado)
        return resultado
