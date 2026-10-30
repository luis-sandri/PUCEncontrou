"""Vocabulário técnico preliminar de erros, sem tratamento HTTP implementado."""


class ErroAplicacao(Exception):
    """Base dos erros esperados; não inclui bugs de programação."""


class ErroValidacao(ErroAplicacao):
    """Dados ou operação inválidos segundo regras aprovadas."""


class OcorrenciaNaoEncontrada(ErroAplicacao):
    """ID solicitado não existe ou não está disponível para a operação."""


class PermissaoNegada(ErroAplicacao):
    """Ator não tem a responsabilidade exigida."""


class FalhaAutenticacao(ErroAplicacao):
    """Falha de autenticação; resposta pública não deve revelar a causa."""


class ErroPersistencia(ErroAplicacao):
    """Leitura ou gravação não concluída; não ocultar perda de dados."""


class ContaNaoEncontrada(ErroAplicacao):
    """Conta de secretário inexistente para a operação solicitada."""


class IdentificadorEmUso(ErroValidacao):
    """Identificador normalizado já pertence a outra conta."""
