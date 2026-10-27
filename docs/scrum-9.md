# SCRUM-9 — Lista Dinâmica baseada em array

Implementação de Marcelo em `app/structures/lista_dinamica.py`.
Branch: `feat/scrum-9-lista-dinamica`, criada a partir do commit `c3e9643`
da SCRUM-8. A branch anterior foi preservada.

## Como executar

No PowerShell:

```powershell
Set-Location C:\xampp2\htdocs\PUCEncontrou
.\.venv\Scripts\python.exe -m pytest tests/unit/test_lista_dinamica.py tests/integration/test_lista_ocorrencias.py -v
.\.venv\Scripts\python.exe -m tests.exemplo_scrum9
.\.venv\Scripts\python.exe -m pytest
```

O primeiro comando de testes cobre a SCRUM-9. O último verifica o projeto todo,
incluindo a SCRUM-8 e a base Flask. Os testes de integração usam modelo, núcleo
CRUD e Lista reais; somente o adaptador entre núcleo e Lista é exclusivo dos
testes, sem persistência ou AVL. A validação local usa Python 3.13 e mantém
sintaxe compatível com o mínimo Python 3.11 declarado no projeto.

## Implementação manual

`ListaDinamica[T]` mantém `_dados` (buffer fixo), `_tamanho` (posições ocupadas),
`_capacidade` (posições alocadas) e `_versao` (controle dos iteradores).

A lista Python é usada somente para alocar `[None] * capacidade`. Não são
usados `append`, `extend`, `insert`, `pop`, `remove`, exclusão ou fatiamento do
buffer para implementar as operações. Inserção, cópia, remoção e expansão
são feitas por atribuição indexada e laços explícitos.

A capacidade inicial padrão é 4, configurável para qualquer inteiro positivo.
Quando o buffer lota, a implementação aloca outro com o dobro da capacidade,
copia os elementos ocupados um a um e troca o buffer. Remover um elemento
desloca os sucessores para a esquerda e limpa a última referência. Não há
redução automática de capacidade.

Essa é uma escolha técnica compatível com a representação de buffer discutida
na documentação. A rubrica específica do professor continua a conferir em
P11; não se presume aprovação externa.

## API

As assinaturas existentes de `ListaDinamicaPorta[T]` foram preservadas.
A classe concreta acrescenta capacidade, busca e filtragem:

```python
ListaDinamica[T](capacidade_inicial: int = 4)
lista.capacidade -> int
lista.inserir(item: T) -> None
lista.obter(indice: int) -> T
lista.atualizar(indice: int, item: T) -> None
lista.remover(indice: int) -> T
len(lista) -> int
iter(lista) -> Iterator[T]
lista.buscar_indice(predicado: Callable[[T], bool]) -> int | None
lista.buscar(predicado: Callable[[T], bool]) -> T | None
lista.filtrar(predicado: Callable[[T], bool]) -> ListaDinamica[T]
```

Inserção ocorre ao final. Remoção preserva a ordem dos demais elementos.
`len` conta os elementos, sem contar posições livres. Índices válidos vão de
0 até `len(lista)-1`; negativos e posições livres geram `IndexError`. Índices
ou capacidades com tipo inválido, inclusive booleanos, geram `TypeError`.
Capacidade menor que 1 gera `ValueError`.

`atualizar` substitui uma posição, sem duplicar o registro ou alterar o tamanho.
IDs pertencem aos objetos e não mudam quando a Lista expande ou desloca
posições. O serviço localiza a posição pelo ID e a substitui pela versão
validada com o mesmo ID. A Lista genérica não valida unicidade de IDs.

Busca é sequencial, retorna a primeira correspondência e usa `None` para
ausência. A estrutura também aceita `None` como elemento; nesse caso,
`buscar_indice` distingue elemento encontrado de ausência.

Predicados são funções que recebem um elemento e indicam se ele atende ao
critério. Predicado inválido gera `TypeError`; exceções não são ocultadas.
Não se deve modificar a Lista dentro do predicado.

## Filtros de ocorrências

A Lista não incorpora regras de formulário, status, contas ou autorização.
Objetos chegam validados pelos serviços. A filtragem genérica permite
consultar os campos necessários sem duplicar regras do modelo:

```python
from app.models.ocorrencia import SituacaoGuarda, StatusOcorrencia, TipoOcorrencia

lista.filtrar(lambda o: o.tipo is TipoOcorrencia.ENCONTRADO)
lista.filtrar(lambda o: o.categoria == "Recipientes")
lista.filtrar(lambda o: o.local_ocorrencia == "Biblioteca")
lista.filtrar(lambda o: o.status is StatusOcorrencia.ABERTO)
lista.filtrar(lambda o: o.setor_guarda == "Bloco 9")
lista.filtrar(lambda o: o.situacao_guarda is SituacaoGuarda.AINDA_NAO_ENTREGUE)
lista.filtrar(lambda o: o.tipo is TipoOcorrencia.ENCONTRADO
                       and o.categoria == "Recipientes")
```

`filtrar` produz outra Lista manual, preservando a ordem. Alterar a estrutura
do resultado não altera a estrutura de origem. As referências dos elementos
são compartilhadas; ocorrências da SCRUM-8 são imutáveis. Para outros tipos
mutáveis, a Lista não faz cópia profunda dos objetos.

Na camada de serviços, `NucleoOcorrencias.listar` já oferece filtros nomeados
combinados. Os testes verificam seus resultados com a Lista real, distinguindo
local da perda/achado, setor de guarda e condição ainda não entregue.
Nenhuma informação de recebimento é inferida.

## Percorrimento e complexidade

Cada `iter(lista)` cria um iterador independente sobre posições ocupadas.
Inserção, remoção ou atualização durante um percorrimento ativo gera
`RuntimeError` na próxima verificação. Isso não substitui locks e não oferece
segurança entre threads.

| Operação | Custo |
| --- | --- |
| Tamanho, capacidade, acesso e atualização por índice | O(1) |
| Inserção sem expansão | O(1) |
| Inserção com expansão | O(n); amortizado O(1) por inserção |
| Remoção | O(n), devido ao deslocamento |
| Busca e percorrimento | O(n) |
| Filtragem | O(n), com espaço adicional proporcional ao resultado |
| Buffer principal | O(capacidade) |

Custos dos predicados são adicionais. A Lista não promete busca por ID em
O(1) e não substitui o índice AVL para consultas temporais.

## Verificação e limites

Testes cobrem lista vazia, índices inválidos, inserção, remoção no início,
meio e fim, expansão repetida até 257 objetos, busca ausente, filtro sem
resultados, atualização sem duplicação, liberação de referência removida,
iteradores independentes e alterações durante percorrimento. Uma sequência
determinística de 500 operações compara resultados com um oráculo de teste.

Testes com ocorrências reais verificam foto preservada, guarda/local/data de
recebimento separados, correções, vínculos, resolução/reabertura, exclusão,
conflitos e reconstrução pelo codec da SCRUM-8. Coleções prontas usadas como
oráculo ou snapshot nos testes não substituem a Lista de produção.

A estrutura não acessa arquivos, não valida fotos, não armazena contas nem
confirma vínculos. O adaptador de memória é exclusivo dos testes. Sincronização
real de Lista/AVL/JSON continua em SCRUM-13; serviços protegidos, uploads e
rotas continuam em SCRUM-16. Nenhuma alteração foi feita na fábrica Flask ou
nos módulos dos colegas.

## Texto para compartilhar com a equipe

Implementei a SCRUM-9 com uma Lista Dinâmica genérica baseada em buffer de
tamanho fixo. O crescimento, a cópia e o deslocamento dos elementos são
manuais. Ela permite inserir, consultar, atualizar, remover, buscar e filtrar,
preservando os registros e IDs. Os filtros distinguem local da ocorrência e
setor de guarda, inclusive itens ainda não entregues. Testei a Lista junto
com o modelo e o núcleo CRUD da SCRUM-8. A integração com JSON e AVL permanece
na SCRUM-13.
