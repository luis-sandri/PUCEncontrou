# Correspondências — André

Implementação isolada em `app/services/correspondencias.py`, na branch
`feature/correspondencias-andre`. Não registra endpoints nem altera a fábrica.
O Jira não pôde ser consultado nesta entrega: busca Rovo e consulta JQL do
conector retornaram `Unknown tool`. Não foram confirmados card, descrição ou
critérios de aceitação. A referência utilizada foi a documentação local,
especialmente regras de negócio, contratos e P03 de `pendencias.md`.

## Consumo

`Correspondencias(leitura, configuracao)` implementa a assinatura existente
`CorrespondenciasPorta.sugerir(id)`. A dependência é `LeituraOcorrenciasPorta`,
usando somente `obter` e `listar`, com instâncias completas e validadas de
`Ocorrencia` (como as retornadas pelo núcleo SCRUM-8). O protocolo mínimo
`OcorrenciaPorta`, sozinho, não descreve os atributos necessários à pontuação;
um adaptador que entregue apenas identidade/tipo/status é rejeitado com
`ErroValidacao`, em vez de produzir sugestões incompletas.

O retorno é uma tupla de `CandidatoCorrespondencia`, com `ocorrencia_id`
(campo exigido pelo protocolo existente) e `pontuacao` em 0–100. O protocolo
não foi ampliado: consumidores que só conhecem IDs continuam compatíveis.
Sem candidatos, retorna `()`. ID inexistente propaga `OcorrenciaNaoEncontrada`
da dependência. Falhas de leitura não são convertidas em resultado vazio.

```python
from app.services.correspondencias import (
    ConfiguracaoCorrespondencias,
    Correspondencias,
)

# Experimento P03; a janela de 10 dias é escolha provisória de demonstração.
configuracao = ConfiguracaoCorrespondencias(
    peso_categoria=30, peso_cor=20, peso_local=20,
    peso_data=20, peso_descricao=10,
    limiar=60, limite=5, janela_dias=10,
)
servico = Correspondencias(leitura=nucleo, configuracao=configuracao)
candidatos = servico.sugerir("id-da-ocorrencia-perdida")
```

O exemplo pressupõe um `nucleo` já composto pelos responsáveis. O serviço
não instancia protocolos, armazenamento, Lista, AVL ou repositório. Na futura
integração HTTP, Luís deve compor a dependência e preparar a visão pública dos
candidatos, aplicando a política de acesso acordada pela equipe. Não há rota
de correspondências ativa ou política de acesso nova nesta entrega.

## Algoritmo e decisões provisórias

1. Obtém a origem; se não estiver ABERTO e sem vínculo, retorna vazio.
2. Lê os registros e elimina repetições idênticas por ID. Estados diferentes
   para o mesmo ID, inclusive o da origem, causam `ErroValidacao`.
3. Seleciona somente registros de tipo oposto, ABERTO e sem vínculo,
   excluindo a própria origem. Funciona nos dois sentidos.
4. Calcula evidências e a soma ponderada, dividida pela soma de **todos** os
   pesos e multiplicada por 100. Ausências valem zero, sem redistribuir pesos.
5. Mantém pontuações positivas maiores ou iguais ao limiar; ordena pela
   pontuação decrescente, desempata por ID crescente e aplica o limite.

As escolhas abaixo são **experimentais de implementação, não regras finais
aprovadas**. A configuração é obrigatória e imutável, sem valores padrão.
Pesos devem ser finitos, não negativos e ter soma positiva; limiar deve estar
em 0–100, limite ser inteiro positivo e janela ser inteiro não negativo.

| Atributo | Evidência de 0 a 1 |
| --- | --- |
| Categoria, cor e local | Igualdade após normalização; vazio nunca é igualdade |
| Data | `max(0, 1 - diferença_absoluta_em_dias / janela_dias)` |
| Descrição | Jaccard: quantidade de termos comuns / quantidade de termos distintos na união |

Normalização ignora caixa, acentos, pontuação e espaços repetidos. Não faz
correção ortográfica, sinônimos, stemming ou remoção de palavras comuns.
A descrição usa termos únicos; repetição não aumenta a evidência. O nome
não recebe peso separado nesta versão, seguindo os cinco atributos de P03.
Foto, guarda, recebimento e destinação não entram no cálculo. Local significa
`local_ocorrencia`, nunca `setor_guarda`.

Janela zero pontua apenas datas iguais. Com janela positiva, a contribuição
da data zera na distância igual ou superior à janela; isso não exclui por si
só o candidato. Não se exige ordem cronológica entre perda e achado nesta
versão. Categoria diferente zera seu peso, sem veto absoluto. As políticas de
janela, incompatibilidade por categoria e evidência mínima exigem calibragem
com a equipe. Com os pesos do exemplo, categoria isolada rende 30/100, abaixo
do limiar 60. Alterar pesos e limiar pode permitir sugestões mais fracas.

A pontuação é um índice de similaridade, não probabilidade de propriedade.
Não é arredondada para filtrar ou ordenar; a interface poderá formatá-la.
O desempate por ID é uma decisão técnica para repetibilidade.

## Exemplo para apresentação

Uma mochila PERDIDO e uma mochila ENCONTRADO, ambas ABERTO e sem vínculo:

| Campo | Perdido | Encontrado |
| --- | --- | --- |
| Nome | Mochila perdida | Mochila encontrada |
| Categoria | Mochila | mochila |
| Cor | Azul | azul |
| Local da ocorrência | Biblioteca | biblioteca |
| Data | 01/11/2026 | 02/11/2026 |
| Descrição | mochila azul com chaveiro | mochila azul com chaveiro |

Com a configuração acima: categoria 30 + cor 20 + local 20 + data 18 +
descrição 10 = **98/100**. A ocorrência encontrada aparece como sugestão.
Nenhum registro é vinculado ou resolvido. Um secretário ainda precisa
confirmar o vínculo e, posteriormente, a devolução presencial pelos serviços
protegidos existentes.

## Integração e limites

Somente objetos imutáveis são lidos. O dicionário temporário serve para
deduplicar o resultado desta chamada; não substitui a Lista acadêmica, a AVL
nem o JSON de produção. Para n registros e k candidatos, o custo é O(n +
k log k), além do processamento dos textos, com memória O(n).

A dependência deverá fornecer leituras coerentes entre `obter` e `listar`.
A verificação de IDs divergentes não substitui o controle de concorrência
do armazenamento. As sugestões podem ficar desatualizadas; o núcleo deve
revalidar as condições no momento de vincular.

Continuam pendentes composição de produção com Lista/AVL/JSON, consumo
HTTP/frontend, revisão e calibragem de P03 e testes de integração. Esta
entrega não implementa esses módulos nem adiciona suíte automatizada.

## Verificações desta entrega

Foram executados `python -m compileall -q app/services/correspondencias.py`
com o interpretador da `.venv`, importação do serviço e uma execução isolada
com ocorrências sintéticas e uma fonte de leitura em memória, sem persistência.
As asserções verificaram o exemplo 98/100, os dois sentidos, exclusão de
encerrados/vinculados/tipo igual, ausência de mutação, ID inexistente,
deduplicação, rejeição de IDs divergentes, desempate, limite, fronteira do
limiar, ausências, normalização, Jaccard parcial, janela zero e configuração
inválida. Todas passaram. `git diff --check` também passou.

Não foi executada a suíte pytest existente nem foram criados testes de
integração. Essas verificações básicas não representam cobertura completa,
validação estatística dos pesos ou integração com Flask/Lista/AVL/JSON.

Na revisão posterior solicitada pelo usuário, a suíte existente foi executada
com `python -m pytest --basetemp .tools/pytest-correspondencias-verificacao -q`:
**298 passaram e 1 falhou**. O único teste com falha foi
`tests/unit/test_fotos.py::test_link_simbolico_nao_permite_ler_fora_da_raiz`,
durante a criação do link simbólico, com `WinError 1314` (privilégio ausente
no Windows), antes de exercitar a leitura da foto. A repetição isolada fora
do sandbox teve o mesmo erro. A execução inicial sem `--basetemp` foi
interrompida após erros na preparação dos diretórios temporários. Não foram
adicionados testes nem alterados os existentes. Esse resultado não cobre a
integração futura do novo serviço, que permanece desconectado das rotas.
