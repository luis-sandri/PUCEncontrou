"""Integração futura de Matheus com Marcelo, Leandro e Luís.

Esboço de composição (não implementado, não chamado pela fábrica):

inicializar_ocorrencias(
    repositorio: RepositorioOcorrenciasPorta,
    lista: ListaDinamicaPorta[OcorrenciaPorta],
    indice: IndiceDatasPorta,
    extrair_data: Callable[[OcorrenciaPorta], date],
) -> None

Carregar e validar o snapshot JSON, preencher a Lista manual e reconstruir
a AVL. Não assumir qual campo de data será indexado; ver docs/pendencias.md.
Falhas não devem deixar um estado parcialmente inicializado utilizável.
"""
