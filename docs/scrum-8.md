# SCRUM-8 — Modelo e núcleo CRUD

Implementação de Marcelo, conforme desenho aprovado pelo solicitante em
27/10/2026. Branch local: `feat/scrum-8-ocorrencias`.

## Executar e conferir

No PowerShell, a partir da raiz do clone:

```powershell
Set-Location C:\xampp2\htdocs\PUCEncontrou
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m tests.exemplo_scrum8
```

O ambiente `.venv` foi preparado localmente usando as dependências existentes
de `requirements.txt`. Nesta máquina, a validação usa Python 3.13; o código
mantém sintaxe compatível com o mínimo declarado pelo projeto, Python 3.11.
Outras versões não foram executadas nesta entrega.

O exemplo usa registros fictícios e armazenamento fake, localizado em `tests/`.
Ele demonstra cadastro, consulta, vínculo, devolução, reabertura, desistência,
exclusão e codec. Não grava JSON nem cria contas, fotos ou endpoints.

## Arquivos e responsabilidades

| Arquivo | Responsabilidade |
| --- | --- |
| `app/models/ocorrencia.py` | Enums, modelo imutável, validação e codec de registro |
| `app/models/alteracao_ocorrencias.py` | Estados anteriores/posteriores, precondições e integridade dos lotes |
| `app/services/nucleo_ocorrencias.py` | Preparação de CRUD, filtros e transições; aplicação por porta injetada |
| `app/erros.py` | Inclui `ConflitoAlteracao` no vocabulário comum |
| `tests/unit/test_ocorrencia.py` | Foto, campos, datas, guarda, identidade e codec |
| `tests/unit/test_alteracao_ocorrencias.py` | Integridade, precondições e snapshots sem alteração da origem |
| `tests/unit/test_nucleo_ocorrencias.py` | Operações reais do núcleo com infraestrutura fake |
| `tests/exemplo_scrum8.py` | Demonstração executável de estudo |

## Contrato do modelo

`Ocorrencia` é uma dataclass `frozen`, com `slots` e argumentos nomeados.
Não se altera um objeto obtido por consulta. Correções produzem uma nova versão
com o mesmo ID; as versões são comparadas integralmente ao confirmar um lote.

| Campo | Tipo no domínio | Regra desta implementação |
| --- | --- | --- |
| `id` | `str` | UUID gerado por `criar`; opaco e preservado na recarga |
| `tipo` | `TipoOcorrencia` | `PERDIDO` ou `ENCONTRADO`; não editável |
| `nome` | `str` | Obrigatório |
| `categoria` | `str` | Obrigatória; sem enum fechado enquanto categorias finais estão pendentes |
| `descricao` | `str` ou `None` | Opcional, aceita múltiplas linhas |
| `cor` | `str` ou `None` | Opcional |
| `data_ocorrencia` | `date` | Obrigatória; data da perda/achado, sem horário |
| `local_ocorrencia` | `str` | Obrigatório; não representa o setor de guarda |
| `status` | `StatusOcorrencia` | Novo registro sempre `ABERTO` |
| `foto_referencia` | `str` | Obrigatória nos dois tipos; caminho relativo local com `/` |
| `situacao_guarda` | `SituacaoGuarda` ou `None` | Somente achados: `AINDA_NAO_ENTREGUE` ou `EM_SETOR` |
| `setor_guarda` | `str` ou `None` | Obrigatório para `EM_SETOR`; ausente para ainda não entregue |
| `data_recebimento` | `date` ou `None` | Opcional, somente em setor; nunca inferida da data do achado |
| `destinacao_a_verificar` | `bool` | Somente achados; não implementa doação ou prazo |
| `vinculo_id` | `str` ou `None` | ID do parceiro; nunca posição da Lista |

As obrigatoriedades de nome/categoria/data/local são escolhas provisórias do
desenho aprovado pelo solicitante, sem alegar aprovação coletiva da lista final.
Textos são aparados nas bordas; descrição/cor/setor opcionais vazios viram `None`.
PERDIDO rejeita dados de guarda, recebimento ou destinação.

Referência válida no modelo é uma referência relativa, não vazia, sem caminhos
absolutos, URL, barras invertidas ou componentes `.`/`..`. Exemplo:
`ocorrencias/abc.jpg`. Extensão, conteúdo, tamanho, existência física e associação
ao upload devem ser validados pelo serviço SCRUM-16. O modelo não abre arquivos
e esta implementação não afirma cumprir sozinha a validação física de foto.

```python
Ocorrencia.criar(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.corrigir(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.para_registro() -> dict[str, object]
Ocorrencia.de_registro(registro: Mapping[str, object]) -> Ocorrencia
```

`criar` não aceita ID, status, vínculo ou campos desconhecidos. `corrigir` também
não aceita tipo. Datas de entrada do domínio são `date`, sem aceitar `datetime`
ou strings implicitamente. A conversão de formulário pertence ao serviço.

O codec usa valores textuais dos enums, booleano JSON e datas `AAAA-MM-DD`;
campos opcionais ausentes são aceitos e campos desconhecidos são rejeitados.
ID, tipo, status e campos mínimos são obrigatórios na recarga. Ele não define
envelope/versionamento do arquivo de Matheus, nem faz I/O. Registros sem foto
são rejeitados explicitamente; não há migração silenciosa ou regravação de
legados. O responsável pela persistência deve interromper a carga inválida
sem substituir o arquivo original por vazio.

## Contrato das operações internas

`NucleoOcorrencias(armazenamento)` não autentica usuários e não deve ser
instanciado por uma rota nem chamado diretamente pelo navegador. Ele é a
dependência interna do futuro serviço protegido, não a implementação do
protocolo externo `ServicoOcorrenciasPorta`, cujas assinaturas foram preservadas.

```python
obter(ocorrencia_id: str) -> Ocorrencia
listar(filtros: Mapping[str, object] | None = None) -> tuple[Ocorrencia, ...]
preparar_cadastro(dados: Mapping[str, object]) -> LoteOcorrencias
preparar_edicao(ocorrencia_id: str, dados: Mapping[str, object]) -> LoteOcorrencias
preparar_exclusao(ocorrencia_id: str) -> LoteOcorrencias
preparar_vinculo(perdido_id: str, encontrado_id: str) -> LoteOcorrencias
preparar_resolucao(ocorrencia_id: str) -> LoteOcorrencias
preparar_reabertura(ocorrencia_id: str) -> LoteOcorrencias
preparar_cancelamento(ocorrencia_id: str) -> LoteOcorrencias
confirmar(lote: LoteOcorrencias) -> None
```

Preparar uma operação não muda o estado. Para desistir, descartar o lote.
`confirmar` pede ao armazenamento que verifique e aplique o lote inteiro.
Não confundir esse método de aplicação com a confirmação presencial de
propriedade: a confirmação presencial e a permissão são responsabilidade do
secretário e do serviço SCRUM-16 antes de solicitar a operação ao núcleo.
Cadastro/consulta são públicos por regra do projeto; demais permissões serão
protegidas nos serviços, sem herança implícita de poderes pelo administrador.

Filtros aceitos: `tipo`, `categoria`, `local_ocorrencia`, `status`,
`situacao_guarda` e `setor_guarda`. Usam igualdade e são combinados por E.
Filtros inválidos são rejeitados; nenhuma correspondência retorna tupla vazia.
Para consultar guarda ainda não entregue:

```python
nucleo.listar({"situacao_guarda": "AINDA_NAO_ENTREGUE"})
```

## Transições

| Operação | Precondição | Resultado |
| --- | --- | --- |
| Cadastro | Dados válidos | Novo ID, ABERTO, sem vínculo |
| Vínculo | PERDIDO e ENCONTRADO abertos, ambos sem parceiro | Referências recíprocas 1:1; continuam ABERTO |
| Resolução | ABERTO | RESOLVIDO; inclui ambos se vinculados |
| Reabertura | RESOLVIDO ou CANCELADO | ABERTO; inclui ambos e mantém vínculo se houver |
| Cancelamento | ABERTO isolado | CANCELADO |
| Exclusão física | Registro existente | Remove registro e limpa vínculo no parceiro, preservando dados/status deste |

Resolver cancelado exige reabertura prévia. Repetir uma transição para o mesmo
status é inválido. Cancelamento de par é rejeitado até definição de sua política.
Não há substituição/desvinculação autônoma, nem sugestão automática de vínculo.
Correspondência recebe só leitura; nenhum algoritmo foi implementado aqui.

## Integração de Lista, AVL e JSON — SCRUM-13

O responsável implementará `ArmazenamentoOcorrenciasPorta`:

```python
obter(ocorrencia_id: str) -> Ocorrencia | None
listar() -> Iterable[Ocorrencia]
aplicar(lote: LoteOcorrencias) -> None
```

`LoteOcorrencias.alteracoes` é uma tupla de `AlteracaoOcorrencia(anterior,
posterior)`. Cadastro tem anterior `None`; exclusão tem posterior `None`;
edição possui ambos, com mesmo ID e tipo. Em pares, as alterações aparecem
no mesmo lote. `alteracao.id` continua disponível inclusive na exclusão.

`lote.preparar_estado(snapshot_atual)` verifica IDs únicos, anteriores,
vínculos e estado final, retornando snapshot temporário sem modificar a origem.
Se algum anterior não coincide, lança `ConflitoAlteracao`: refazer a operação
com leitura atual em vez de sobrescrever a correção de outro usuário. Essa
comparação considera os valores, não um contador histórico de revisões.

A implementação real deve verificar as precondições **dentro do mesmo lock**
da publicação. Deve preparar os estados novos, coordenar gravação e publicação
de Lista/AVL/JSON e preservar os estados anteriores se falhar. Não aplicar o
primeiro parceiro e só depois validar o segundo. O helper de snapshot sozinho
não oferece lock, rollback de arquivo ou coordenação entre processos.

Correção de data fornece `anterior.data_ocorrencia` e
`posterior.data_ocorrencia` com o mesmo ID; a integração pode remover a chave
antiga da AVL e inserir a nova. Exclusão fornece o registro anterior completo.
A indexação continua sob a política acordada com Leandro, sem expor nós.

Os snapshots e coleções auxiliares deste núcleo são temporários para validar
operações. Não constituem armazenamento principal e não cumprem SCRUM-9:
a produção deverá usar a Lista Dinâmica manual.

## Erros e limites de entrega

`ErroValidacao`: campo, transição, filtro ou vínculo inválido;
`OcorrenciaNaoEncontrada`: ID inexistente;
`ConflitoAlteracao`: lote obsoleto;
`ErroPersistencia`: pode ser propagado pela futura integração de armazenamento.
Falhas não são transformadas em sucesso ou lista vazia silenciosamente.

O núcleo e codec estão implementados e testados. Ainda não há CRUD acessível
pela página, validação dos bytes da foto, armazenamento real por Lista/AVL/JSON,
migração de legados ou gestão de contas. Nenhum desses módulos de colegas foi
substituído por implementação pronta. A adequação dos esboços antigos de contas
de SQLite para JSON continua com seu responsável.
