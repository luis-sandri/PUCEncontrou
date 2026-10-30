# Contratos iniciais v0 e módulo experimental de contas

**Estado: esboços técnicos propostos para revisão dos responsáveis.**
As regras explicitamente aprovadas estão em [regras de negócio](regras-negocio.md).
Os nomes, tipos auxiliares, retornos e convenções desta página não são uma
aprovação da equipe. As anotações de código são pontos de partida para
desenvolvimento com fakes, sem implementar os módulos dos colegas.

Cada `Porta` é um `typing.Protocol`, não uma classe concreta. Ninguém deve
instanciá-la nem herdar dela para receber uma implementação padrão. A
implementação futura pode satisfazer o contrato por suas assinaturas.
Não há validação de conformidade em runtime nesta base.

**Implementação candidata de Luís (30/10/2026):** contas têm contrato executável
experimental descrito abaixo. P09/P10 continuam pendentes; sua implementação
exige opt-in e não registra aprovação coletiva. Demais módulos permanecem v0.

## Convenções e composição propostas

- IDs são strings opacas e estáveis; consumidor não interpreta nem usa posição
  da Lista como ID. UUID, sequência ou outro gerador ainda precisam de revisão.
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
- `ator` vem da autenticação do backend e da conta carregada no SQLite.
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
| Novo registro | Começa `ABERTO`; ID gerado no backend | Status aprovado; estratégia de ID pendente |
| Modelo concreto | Classe `Ocorrencia`, campos e validações | A implementar após P01/P02 |

Assinaturas de codec/modelo para discussão com Matheus, **não implementadas**:

```python
Ocorrencia.criar(dados: Mapping[str, object]) -> Ocorrencia
Ocorrencia.para_registro() -> Mapping[str, object]
Ocorrencia.de_registro(registro: Mapping[str, object]) -> Ocorrencia
```

O codec não deve gerar novo ID, forçar `ABERTO` ao recarregar, perder vínculos
ou confundir os dois locais. A criação não é um atalho para alterar status.
Campos de data, descrição, categoria, cor, contato e vínculos ainda não estão
no protocolo porque obrigatoriedade, representação e exposição dependem da
equipe. Validação não deve ser distribuída em seis versões incompatíveis.

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
- `vincular` não confirma devolução nem altera status automaticamente. O
  ator obrigatório é uma proposta conservadora; quem pode vincular precisa
  de aprovação em P05 antes de expor endpoint ou implementar a autorização.
- `excluir` esconde a estratégia física/lógica do consumidor; efeito em
  consultas, arquivo, índice e vínculos aguarda P04/P05.

O serviço é o único coordenador de mutações da Lista, índice e snapshot.
Não permitir edição direta de objetos retornados para contornar regras.
Definir DTOs/cópias ou imutabilidade no modelo concreto. A estratégia de
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

**Contrato executável experimental desta branch, para revisão.**
`ContaAdministrativa` e `CredenciaisConta` são dataclasses imutáveis.
`ContaAdministrativaPorta` e a visão concreta contêm `id: str`, `perfil: Perfil`,
`nome: str`, `identificador: str` e `ativa: bool`. A credencial privada acrescenta
`senha_hash: str` (omitido do repr) e `para_visao() -> ContaAdministrativa`.
Rotas projetam somente os cinco campos administrativos; não serializam credenciais.

`RepositorioContasSQLite(caminho: Path | str)` não realiza I/O no construtor.
O protocolo `RepositorioContasPorta` e o concreto oferecem:

```python
inicializar() -> None
inicializar_administrador(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativa
buscar_por_id(conta_id: str) -> CredenciaisContaPorta | None
buscar_por_identificador(identificador: str) -> CredenciaisContaPorta | None
salvar_secretario(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativaPorta
listar_secretarios() -> list[ContaAdministrativa]
atualizar_secretario(conta_id: str, dados: Mapping[str, object], *, senha_hash: str | None = None) -> ContaAdministrativa
criar_sessao(conta_id: str, token_hash: str, expira_em: int, *, senha_hash_esperada: str) -> None
buscar_sessao(token_hash: str, agora: int) -> CredenciaisContaPorta | None
revogar_sessao(token_hash: str) -> None
```

O concreto devolve `CredenciaisConta`/`ContaAdministrativa` onde a porta descreve
essas visões. IDs UUID, esquema SQLite v1, SQL parametrizado e escritas com
`BEGIN IMMEDIATE`. Consultas não criam arquivo. Inicialização explícita recusa
versão desconhecida ou banco não vazio sem versão reconhecida, sem apagar dados.
O esquema não cria contas; transação e índice garantem administrador inicial único.

Criação recebe somente `nome` e `identificador`; atualização do repositório
recebe `nome`, `identificador` e/ou `ativa`, com senha já em hash. Só atualiza
secretário. Desativação, redefinição de senha ou mudança do identificador revoga
todas as sessões na mesma transação, com rollback conjunto em falha. A criação
de sessão confirma conta ativa e hash ainda igual ao autenticado para impedir
login com senha antiga após reset concorrente.

```python
# ServicoContas(repositorio: RepositorioContasPorta)
listar_secretarios(*, ator: ContaAdministrativaPorta) -> list[ContaAdministrativa]
cadastrar_secretario(dados: Mapping[str, object], senha: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativa
gerenciar_secretario(conta_id: str, alteracoes: Mapping[str, object], *, ator: ContaAdministrativaPorta) -> ContaAdministrativa

# ServicoAutenticacao(repositorio, duracao_sessao_segundos: int = 1800)
autenticar(identificador: str, senha: str) -> ContaAdministrativa
iniciar_sessao(identificador: str, senha: str) -> tuple[ContaAdministrativa, str]
obter_sessao(token: str) -> ContaAdministrativa | None
encerrar_sessao(token: str) -> None
inicializar_administrador(dados: Mapping[str, object], senha: str) -> ContaAdministrativa
```

As portas dos serviços mantêm retornos `ContaAdministrativaPorta`;
`GestaoContasPorta.listar_secretarios` retorna `Sequence[ContaAdministrativaPorta]`.
Bootstrap é método concreto exclusivo da CLI. Valida entradas, prepara esquema
e insere administrador; repetir recusa substituição. Comando `flask --app app
contas inicializar` pede senha oculta/confirmada e não aceita senha em opção.

Gestão recarrega ator pelo ID no banco e exige administrador ativo, sem confiar
no perfil recebido. Secretário não gerencia contas; administrador não ganha
ações de secretário. `gerenciar_secretario` aceita somente `nome`, `identificador`,
`ativa: false` e/ou `senha`; não há reativação ou exclusão. Campos extras são
recusados, inclusive `perfil`, `ator` e `senha_hash`.

Escolhas provisórias: nome com 1–120 caracteres após `strip`, sem controles;
identificador genérico único com 3–120 caracteres após `strip`/`casefold`, sem
espaços/controles, sem exigir e-mail; senha com 12–128 caracteres Unicode
codificáveis em UTF-8, sem normalização. Hash/verificação são do Werkzeug.
Senha em texto é transitória e não entra em logs, DTOs ou configuração.

Falha de autenticação é genérica para login ausente, incorreto ou inativo.
Sessões usam token de 32 bytes aleatórios; SQLite guarda somente SHA-256 do
token, ID da conta e expiração absoluta em segundos Unix. Logout revoga no
servidor, inclusive cópias antigas de cookie. Prazo inicial de 1.800 segundos
é configurável por `CONTAS_DURACAO_SESSAO_SEGUNDOS` na fábrica.

`CONTAS_HABILITADAS` é booleano (ambiente `PUC_CONTAS_HABILITADAS=true`),
falso por padrão. Só habilitado compõe serviços concretos em
`app.extensions['autenticacao']` e `['contas']` e registra CLI/rotas. A fábrica
não inicializa banco ou administrador e não instancia protocolos.
Veja [como validar e as limitações](desenvolvimento-luis.md).

## HTTP e Jinja2 — Luís e Mariana

**Implementado:** `GET /`, endpoint `publicas.inicio`, template `index.html`,
sem contexto de domínio, mais o endpoint estático padrão do Flask.

**Contas por opt-in:** API JSON experimental, sem telas novas. `GET /login`
entrega CSRF; `POST /login` autentica e rotaciona CSRF; `GET /sessao` entrega
`{conta, csrf_token}`; `POST /logout` revoga a sessão (204). Gestão usa
`GET/POST /contas/secretarios` e `PATCH /contas/secretarios/<id>`.
Não há cadastro público de administrador nem rotas de ocorrências registradas.

Mutações exigem JSON e `X-CSRF-Token` do mesmo cookie. Cookie HttpOnly e
SameSite=Lax, Secure configurável para HTTPS, sem ID/perfil/hash. A conta ativa
é recarregada em cada requisição. Respostas usam `Cache-Control: no-store`;
corpos limitados a 16 KiB. A visão tem somente os cinco campos acima.
Cadastro retorna 201; login/sessão/alteração retornam 200.
Erros `{erro: str}`: 400 validação, 401 sem autenticação/falha login, 403 perfil
ou CSRF, 404 conta ausente, 409 identificador duplicado, 413 corpo excessivo,
415 conteúdo sem JSON, 503 persistência (mensagem genérica).
O [guia de validação](desenvolvimento-luis.md) lista payloads e limitações.

**Mapa de integração: ocorrências futuras; contas implementadas por opt-in.**

| Fluxo | Caminho/método proposto | Serviço/controle | Dependências para fechar contrato |
| --- | --- | --- | --- |
| Listar/detalhar | `GET /ocorrencias`, `GET /ocorrencias/<id>` | Consulta pública; contexto Jinja de visão pública | Campos públicos, filtros, ordem e paginação |
| Cadastrar | `GET/POST /ocorrencias/nova` | `cadastrar`, sem login | Campos e mensagens validados |
| Editar/excluir | `POST /ocorrencias/<id>/editar`, `POST /ocorrencias/<id>/excluir` | Serviço + SECRETARIO | Campos, exclusão e proteção CSRF |
| Status | `POST /ocorrencias/<id>/status` | Serviço + SECRETARIO | Contexto de confirmação/cancelamento e CSRF |
| Vínculo | `POST /ocorrencias/vinculos` | `vincular`; ator a confirmar | Política P05 e CSRF |
| Login/logout | `GET/POST /login`, `GET /sessao`, `POST /logout` | API experimental protegida | Validar P09/P10 e integrar telas |
| Contas de secretários | `GET/POST /contas/secretarios`, `PATCH /contas/secretarios/<id>` | API experimental + ADMINISTRADOR | Validar P09/P10 e integrar telas |

Para os fluxos futuros de ocorrências, não habilitar mutação via GET. Antes da integração, escolher formulários
Jinja/redirect ou respostas JSON por fluxo; não há API REST definitiva.
Contextos com nomes/campos exatos e mensagens ainda não foram definidos;
Mariana usa fixtures visuais locais explicitamente fictícias até a revisão.

Proposta para formulários: erro validado reexibe tela com valores seguros;
sucesso usa redirect após POST. Proposta para API, se adotada: 400 para
validação, 401 sem autenticação, 403 sem permissão, 404 ID inexistente;
falhas de I/O com resposta genérica e logs sem segredos. Não tratar todo
`Exception` como erro de usuário. Esse rascunho ainda não está ativo para ocorrências.

## Erros e revisão de mudanças

`app/erros.py` oferece um vocabulário inicial: `ErroValidacao`,
`OcorrenciaNaoEncontrada`, `PermissaoNegada`, `FalhaAutenticacao`,
`ErroPersistencia`, mais `ContaNaoEncontrada` e `IdentificadorEmUso` para contas.
Estruturas usam erros de índice/comparação, sem importar
erros HTTP. As rotas futuras traduzem erros do serviço para a experiência
escolhida, sem expor stack trace ou caminhos internos.

Antes de integrar, responsável e consumidores revisam assinatura, retorno,
erros, efeitos colaterais e dependência Pxx. A PR atualiza este documento,
anota aprovação real quando existir e inclui testes do contrato implementado.
Não usar esta documentação como autorização para resolver pendências de negócio.
