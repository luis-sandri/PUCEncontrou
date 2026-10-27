# Contratos iniciais v0

## Atualização SCRUM-8 — 27/10/2026

O modelo concreto e o núcleo interno foram implementados conforme desenho
aprovado por Marcelo. Seu contrato vigente está em [SCRUM-8](scrum-8.md):
`Ocorrencia`, `SituacaoGuarda`, `AlteracaoOcorrencia`, `LoteOcorrencias`,
`NucleoOcorrencias` e `ArmazenamentoOcorrenciasPorta`. Essa seção e o guia
substituem os trechos v0 divergentes abaixo sobre modelo e CRUD interno.

Os protocolos externos `LeituraOcorrenciasPorta` e `ServicoOcorrenciasPorta`
mantêm suas assinaturas: são esboços do serviço autenticado de SCRUM-16,
não a classe interna `NucleoOcorrencias`. Nenhuma rota nova foi registrada.
SCRUM-13 implementará a porta de aplicação atômica com Lista/AVL/JSON.
Foto é obrigatória nos dois tipos. Contas passam a JSON; referências antigas
a SQLite descrevem a preparação anterior e aguardam ajuste do módulo de contas.

**Estado: esboços técnicos propostos para revisão dos responsáveis.**
As regras explicitamente aprovadas estão em [regras de negócio](regras-negocio.md).
Os nomes, tipos auxiliares, retornos e convenções desta página não são uma
aprovação da equipe. As anotações de código são pontos de partida para
desenvolvimento com fakes, sem implementar os módulos dos colegas.

Cada `Porta` é um `typing.Protocol`, não uma classe concreta. Ninguém deve
instanciá-la nem herdar dela para receber uma implementação padrão. A
implementação futura pode satisfazer o contrato por suas assinaturas.
Não há validação de conformidade em runtime nesta base.

## Convenções e composição propostas

- IDs são strings opacas e estáveis; consumidor não interpreta nem usa posição
  da Lista como ID. O modelo concreto gera UUID textual e preserva IDs na recarga.
- `date` representa uma chave de calendário já convertida pelo serviço.
  Não escolher implicitamente entre data de perda/achado e data de cadastro.
- `Iterable`/`Iterator` são retornos percorríveis, sem promessa de `list`,
  paginação ou ordem geral. Exceção: consulta temporal propõe ordem por data.
- `Mapping[str, object]` reserva o espaço de entradas/filtros/contexto enquanto
  os campos não forem aprovados. Deve ser substituído por DTOs revisados;
  não autoriza campos arbitrários, mass assignment nem repasse de `request.form`.
- Métodos de estruturas não conhecem Flask, perfis, JSON ou SQLite.
- Serviços recebem suas dependências por construtor; a fábrica futura registra
  as instâncias. Rotas não criam serviços, não importam uma app global e não
  instanciam estruturas por requisição.
- `ator` vem da autenticação do backend e da conta carregada na persistência de contas.
  Não confiar em ID/perfil enviados pelo navegador. Sem ator válido, negar
  mutações protegidas. O serviço valida permissão além da proteção da rota.
- Dados públicos são projetados em DTO/contexto de template; objetos do modelo,
  hashes e dados de contato não são serializados integralmente por conveniência.

Composição futura ilustrativa, **somente rascunho de construtor**:

```python
ServicoOcorrencias(
    lista: ListaDinamicaPorta[OcorrenciaPorta],
    indice: IndiceDatasPorta,
    repositorio: RepositorioOcorrenciasPorta,
    extrair_data: Callable[[OcorrenciaPorta], date],
)
ConsultaPeriodo(indice: IndiceDatasPorta, obter: Callable[[str], OcorrenciaPorta])
Correspondencias(leitura_ocorrencias: LeituraOcorrenciasPorta, politica: object)
```

`LeituraOcorrenciasPorta` contém somente `obter` e `listar`; o protocolo de
CRUD a estende. Correspondência usa essa porta restrita e não recebe métodos
de mutação como dependência. `politica` é marcador provisório,
sem pesos, limiar ou algoritmo aprovados. Não criar framework de injeção.

## Modelo de ocorrência — Marcelo

Código: `app/models/ocorrencia.py`.

| Elemento | Contrato inicial | Estado |
| --- | --- | --- |
| Tipo | `TipoOcorrencia.PERDIDO`, `.ENCONTRADO` | Vocabulário do contexto |
| Status | `StatusOcorrencia.ABERTO`, `.RESOLVIDO`, `.CANCELADO` | Aprovado |
| Visão mínima | `OcorrenciaPorta.id: str`, `.tipo: TipoOcorrencia`, `.status: StatusOcorrencia` | Propriedades de leitura propostas |
| Novo registro | Começa `ABERTO`; UUID textual no backend | Implementado em SCRUM-8 |
| Modelo concreto | Classe imutável `Ocorrencia`, campos e validações | Implementado; campos detalhados no guia |

Assinaturas de codec/modelo implementadas; integração de arquivo com Matheus:

```python
Ocorrencia.criar(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.corrigir(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.para_registro() -> dict[str, object]
Ocorrencia.de_registro(registro: Mapping[str, object]) -> Ocorrencia
```

O codec não deve gerar novo ID, forçar `ABERTO` ao recarregar, perder vínculos
ou confundir os dois locais. A criação não é um atalho para alterar status.
Campos concretos de data, descrição, categoria, cor, foto, guarda e vínculos
estão no modelo e no guia; o protocolo mínimo de leitura permanece compatível.
Não foram adicionados dados de contato. Exposição pública depende do serviço.
Validação não deve ser distribuída em seis versões incompatíveis.

## Lista Dinâmica — Marcelo

Código: `app/structures/lista_dinamica.py`.

```python
inserir(item: T) -> None
obter(indice: int) -> T
atualizar(indice: int, item: T) -> None
remover(indice: int) -> T
__len__() -> int
__iter__() -> Iterator[T]
```

Convenção proposta: inserir ao final; preservar ordem dos demais elementos;
`len` retorna quantidade de elementos ocupados, não capacidade; iterar apenas
elementos ocupados. `obter`, `atualizar` e `remover` usam índices entre 0 e
`len-1` e lançam `IndexError` para inválidos, inclusive negativos. A equipe
pode ajustar essa convenção antes de implementar consumidores.

Busca por ID, regras de status e validações do domínio ficam no serviço.
Capacidade inicial, fator de crescimento e representação do array ficam com
Marcelo conforme rubrica acadêmica (P11). Não há implementação de buffer,
redimensionamento ou inserção nesta base.

## AVL e consulta temporal — Leandro

Códigos: `app/structures/avl.py`, `app/services/consultas.py`.

```python
# Índice auxiliar, sem retornar nós
inserir(data: date, ocorrencia_id: str) -> None
remover(data: date, ocorrencia_id: str) -> None
buscar_periodo(inicio: date, fim: date) -> Iterator[str]

# Serviço resolve os IDs contra registros existentes
buscar_periodo(inicio: date, fim: date) -> Iterable[OcorrenciaPorta]
```

Convenções propostas para revisão: limites inclusivos; IDs em ordem crescente
de data, sem ordem de desempate prometida; mais de um ID na mesma data;
par `(data, id)` único. Inserir par existente não duplica resultado e remover
par ausente não remove outro ID. Índice vazio retorna iterador vazio.

Início maior que fim é erro de validação no serviço; fronteiras diretas da
estrutura precisam definir se usam `ValueError` (proposta) antes da implementação.
Mudança da data indexada remove o par antigo e insere o novo, coordenada pelo
serviço. A AVL não recebe posições da Lista e não é a fonte dos registros.
Qual data, ausência de data, timezone e empates são P02, ainda pendentes.

## Persistência JSON e reconstrução — Matheus

Código: `app/repositories/json_ocorrencias.py`.

```python
carregar() -> Iterable[OcorrenciaPorta]
salvar(ocorrencias: Iterable[OcorrenciaPorta]) -> None
```

O caminho e codec são dependências do repositório futuro. `carregar` devolve
registros do domínio, nunca nós AVL nem uma Lista global. `salvar` recebe o
snapshot completo e não altera objetos recebidos nem atualiza estruturas.
O formato externo versionado é proposta; nenhum esquema JSON foi imposto.

Condições técnicas propostas: UTF-8, datas em representação ISO acordada,
IDs/status/vínculos preservados, erro de leitura/escrita como `ErroPersistencia`,
arquivo inválido jamais substituído por vazio silenciosamente. Política para
arquivo inexistente, migração e backups deve ser fechada em P07.

`services/inicializacao.py` reserva o seguinte ponto de integração:

```python
inicializar_ocorrencias(
    repositorio: RepositorioOcorrenciasPorta,
    lista: ListaDinamicaPorta[OcorrenciaPorta],
    indice: IndiceDatasPorta,
    extrair_data: Callable[[OcorrenciaPorta], date],
) -> None
```

Este rascunho só existe na documentação/docstring. Exige destinos novos/vazios
ou política explícita de reconstrução; não carregar duas vezes duplicando
registros. Validar snapshot antes de expor os serviços; falha não pode publicar
Lista preenchida parcialmente com AVL inconsistente. IDs duplicados e referências
inexistentes precisam ser detectados. Não chamar `salvar` ao carregar.

## Serviço de ocorrências — Marcelo com revisão de Luís

Código: `app/services/ocorrencias.py`.

```python
cadastrar(dados: Mapping[str, object]) -> OcorrenciaPorta
obter(ocorrencia_id: str) -> OcorrenciaPorta
listar(filtros: Mapping[str, object] | None = None) -> Iterable[OcorrenciaPorta]
editar(ocorrencia_id: str, dados: Mapping[str, object], *, ator: ContaAdministrativaPorta) -> OcorrenciaPorta
excluir(ocorrencia_id: str, *, ator: ContaAdministrativaPorta) -> None
alterar_status(ocorrencia_id: str, novo_status: StatusOcorrencia, *, ator: ContaAdministrativaPorta, contexto: Mapping[str, object]) -> Iterable[OcorrenciaPorta]
vincular(perdido_id: str, encontrado_id: str, *, ator: ContaAdministrativaPorta) -> Iterable[OcorrenciaPorta]
```

- Cadastro e consulta são públicos; `obter` inexistente propõe
  `OcorrenciaNaoEncontrada`; `listar` sem resultados retorna vazio.
- Editar, excluir e alterar status exigem secretário autenticado e não
  restringem bloco. Não deduzir poder de secretário do perfil administrador.
- `alterar_status` retorna **todos os registros alterados**, incluindo par
  resolvido/reaberto. Não deve permitir mudanças de status por edição de campos.
- `contexto` reserva confirmação presencial/justificativa; conteúdo e forma
  de registrar confirmação ainda precisam ser definidos. Receber um boolean
  do cliente não dispensa identidade, autorização e ação do secretário.
- `vincular` não confirma devolução nem altera status automaticamente.
  No desenho SCRUM-8, a ação é do secretário; SCRUM-16 implementará a proteção.
- `excluir` usa exclusão física conforme escolha do usuário. O núcleo prepara
  remoção e limpeza do vínculo; aplicação em Lista/AVL/JSON pertence a SCRUM-13.

O serviço é o único coordenador de mutações da Lista, índice e snapshot.
Não permitir edição direta de objetos retornados para contornar regras.
O modelo concreto já é imutável. A estratégia de
atomicidade memória/JSON é parte da integração P08, não existe nesta base.

## Correspondências — André

Código: `app/services/correspondencias.py`.

```python
CandidatoCorrespondenciaPorta.ocorrencia_id: str
sugerir(ocorrencia_id: str) -> Sequence[CandidatoCorrespondenciaPorta]
```

O contrato mínimo retorna referências a candidatos, sem status alterado ou
afirmação de propriedade. Pontuação, justificativas, ordenação, critérios de
elegibilidade, limite, pesos e valores ausentes precisam de P03. Não há
`5`, `60` ou pesos fixos no código. A política deve ser determinística,
com testes reprodutíveis e sem qualquer provedor de IA.

## Contas, SQLite e autenticação — Luís

Códigos: `app/models/conta.py`, `app/repositories/sqlite_contas.py`,
`app/services/autenticacao.py`, `app/services/contas.py`.

```python
# Visão administrativa sem senha
ContaAdministrativaPorta.id: str
ContaAdministrativaPorta.perfil: Perfil
# Somente repositório e autenticação
CredenciaisContaPorta.senha_hash: str

# Repositório inicial (gestão completa depende de P09)
buscar_por_id(conta_id: str) -> CredenciaisContaPorta | None
buscar_por_identificador(identificador: str) -> CredenciaisContaPorta | None
salvar_secretario(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativaPorta

# Serviços
autenticar(identificador: str, senha: str) -> ContaAdministrativaPorta
cadastrar_secretario(dados: Mapping[str, object], senha: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativaPorta
gerenciar_secretario(conta_id: str, alteracoes: Mapping[str, object], *, ator: ContaAdministrativaPorta) -> ContaAdministrativaPorta
```

SQLite usa parâmetros em consultas e transações, sem SQL montado por entrada
do usuário. Serviços geram/verificam hashes com biblioteca apropriada (por
exemplo Werkzeug); nunca implementam criptografia própria nem armazenam
senha em texto. Senha recebida pelo serviço é transitória e não vai para
logs, DTOs, templates ou arquivos de configuração.

Falha de autenticação propõe `FalhaAutenticacao` com mensagem pública
genérica. Gestão exige administrador no backend; secretário não recebe
operações de gestão. Identificador de login, unicidade, desativação, reset
e campos de conta aguardam P09; as operações do repositório para essa
gestão completa serão adicionadas após a definição. Nenhuma conta padrão.

O bootstrap inicial está reservado em `scripts/README.md`; não há rota,
comando ativo nem senha de administrador nesta etapa.

## HTTP e Jinja2 — Luís e Mariana

**Implementado:** `GET /`, endpoint `publicas.inicio`, template `index.html`,
sem contexto de domínio, mais o endpoint estático padrão do Flask.

**Rascunho de fronteira futura; não registrado:**

| Fluxo | Caminho/método proposto | Serviço/controle | Dependências para fechar contrato |
| --- | --- | --- | --- |
| Listar/detalhar | `GET /ocorrencias`, `GET /ocorrencias/<id>` | Consulta pública; contexto Jinja de visão pública | Campos públicos, filtros, ordem e paginação |
| Cadastrar | `GET/POST /ocorrencias/nova` | `cadastrar`, sem login | Campos e mensagens validados |
| Editar/excluir | `POST /ocorrencias/<id>/editar`, `POST /ocorrencias/<id>/excluir` | Serviço + SECRETARIO | Campos, exclusão e proteção CSRF |
| Status | `POST /ocorrencias/<id>/status` | Serviço + SECRETARIO | Contexto de confirmação/cancelamento e CSRF |
| Vínculo | `POST /ocorrencias/vinculos` | `vincular`; ator a confirmar | Política P05 e CSRF |
| Login/logout | `GET/POST /login`, `POST /logout` | Autenticação backend | Sessão, CSRF, erros e política P09/P10 |
| Contas de secretários | `GET/POST /contas/secretarios` | Gestão + ADMINISTRADOR | Campos, ações, templates e CSRF |

Não habilitar mutação via GET. Antes da integração, escolher formulários
Jinja/redirect ou respostas JSON por fluxo; não há API REST definitiva.
Contextos com nomes/campos exatos e mensagens ainda não foram definidos;
Mariana usa fixtures visuais locais explicitamente fictícias até a revisão.

Proposta para formulários: erro validado reexibe tela com valores seguros;
sucesso usa redirect após POST. Proposta para API, se adotada: 400 para
validação, 401 sem autenticação, 403 sem permissão, 404 ID inexistente;
falhas de I/O com resposta genérica e logs sem segredos. Não tratar todo
`Exception` como erro de usuário. Nada desse tratamento HTTP está ativo.

## Erros e revisão de mudanças

`app/erros.py` oferece um vocabulário inicial: `ErroValidacao`,
`OcorrenciaNaoEncontrada`, `PermissaoNegada`, `FalhaAutenticacao`,
`ErroPersistencia`. Estruturas usam erros de índice/comparação, sem importar
erros HTTP. As rotas futuras traduzem erros do serviço para a experiência
escolhida, sem expor stack trace ou caminhos internos.

Antes de integrar, responsável e consumidores revisam assinatura, retorno,
erros, efeitos colaterais e dependência Pxx. A PR atualiza este documento,
anota aprovação real quando existir e inclui testes do contrato implementado.
Não usar esta documentação como autorização para resolver pendências de negócio.
