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

**Atualização de Luís (30/10/2026):** contas têm contrato executável com
formulários Jinja e sessão Flask. P09/P10 de contas foram definidos por Luís
nesta conversa; a revisão coletiva continua pendente. A configuração explícita
permite testar o módulo. Demais contratos de ocorrências permanecem v0.

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

Contrato atualizado conforme escolhas de Luís em P09/P10, para revisão da equipe.
`ContaAdministrativa` e `CredenciaisConta` são dataclasses imutáveis. A visão
administrativa e `ContaAdministrativaPorta` contêm `id: str`, `perfil: Perfil`,
`nome: str`, `identificador: str`, `ativa: bool`, `versao_sessao: int`.
O identificador é o e-mail `@pucpr.edu.br`. A versão é um contador interno,
**não enviado aos templates**. Rotas projetam somente os outros cinco campos.
A credencial privada acrescenta `senha_hash: str` (omitido do repr) e
`para_visao() -> ContaAdministrativa`.

`RepositorioContasSQLite(caminho: Path | str)` não faz I/O no construtor.
O protocolo `RepositorioContasPorta` e a implementação oferecem:

```python
inicializar() -> None
inicializar_administrador(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativa
buscar_por_id(conta_id: str) -> CredenciaisContaPorta | None
buscar_por_identificador(identificador: str) -> CredenciaisContaPorta | None
salvar_secretario(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativaPorta
listar_secretarios() -> list[ContaAdministrativa]
atualizar_secretario(conta_id: str, dados: Mapping[str, object], *, senha_hash: str | None = None) -> ContaAdministrativa
recuperar_administrador(identificador: str, *, senha_hash: str) -> ContaAdministrativa
```

O concreto retorna `CredenciaisConta`/`ContaAdministrativa` onde a porta descreve
essas visões. Mantém IDs UUID, e-mail único, SQL parametrizado e transações de
escrita. `inicializar` cria o esquema v2 ou migra explicitamente v1 para v2,
preservando contas, IDs e hashes, acrescentando o contador e removendo a tabela
`sessoes` antiga. Consultas/fábrica não migram ou criam arquivos. Banco desconhecido
ou incompatível é recusado sem sobrescrita. A migração exige a CLI; ver guia.

Criação recebe `nome` e `identificador`; atualização recebe `nome`, `identificador`
e/ou `ativa`, com senha já em hash. Só atualiza secretário. Mudança de e-mail,
ativação/desativação ou reset incrementa `versao_sessao` na mesma transação da
alteração. Falha desfaz dados e contador juntos. Editar só nome preserva a sessão.
Bootstrap cria somente o primeiro administrador. Recuperação local mantém seu ID
e nome e altera e-mail/senha, reativa a conta e incrementa o contador.

```python
# ServicoContas(repositorio: RepositorioContasPorta)
listar_secretarios(*, ator: ContaAdministrativaPorta) -> list[ContaAdministrativa]
obter_secretario(conta_id: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativa
cadastrar_secretario(dados: Mapping[str, object], senha: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativa
gerenciar_secretario(conta_id: str, alteracoes: Mapping[str, object], *, ator: ContaAdministrativaPorta) -> ContaAdministrativa

# ServicoAutenticacao(repositorio: RepositorioContasPorta)
autenticar(identificador: str, senha: str) -> ContaAdministrativa
obter_sessao(conta_id: str, versao_sessao: int) -> ContaAdministrativa | None
atualizar_banco() -> None
inicializar_administrador(dados: Mapping[str, object], senha: str) -> ContaAdministrativa
recuperar_administrador(identificador: str, senha: str) -> ContaAdministrativa
```

As portas dos serviços mantêm retornos `ContaAdministrativaPorta`;
`GestaoContasPorta.listar_secretarios` usa `Sequence[ContaAdministrativaPorta]`.
Preparação do banco, bootstrap e recuperação são métodos concretos da CLI local,
sem rota pública. Os antigos `iniciar_sessao`, `encerrar_sessao`, tokens opacos e
operações de tabela de sessões foram retirados; consumidores e testes foram adaptados.

Gestão recarrega o ator por ID e exige administrador ativo no banco. Não confia
em perfil recebido; secretário não gerencia contas e administrador não ganha
poder de secretário. Alterações aceitam `nome`, `identificador`, `ativa: bool`
e/ou `senha`; não há exclusão de conta, gestão de administradores pelo navegador
ou mudança de credenciais próprias. Campos extras são recusados.

Nome tem 1–120 caracteres após `strip`, sem controles. E-mail é normalizado com
`strip`/`casefold`, tem até 120 caracteres, parte local usual e domínio exatamente
`pucpr.edu.br`. Senha tem 12–128 caracteres Unicode codificáveis em UTF-8, sem
normalização; hash/verificação são Werkzeug. Senha não entra em DTO, template,
log ou configuração. Falha de login é genérica para conta ausente/inativa ou senha
incorreta. Limites técnicos permanecem sujeitos à revisão da equipe.

`CONTAS_HABILITADAS` (ambiente `PUC_CONTAS_HABILITADAS=true`) continua falso por
padrão. Quando habilitado, a fábrica compõe serviços concretos em
`app.extensions['autenticacao']` e `['contas']`, registra CLI e formulários.
O prazo `CONTAS_DURACAO_SESSAO_SEGUNDOS` é inteiro positivo, padrão 1800.

## HTTP e Jinja2 — Luís e Mariana

Por padrão, `GET /` (`publicas.inicio`) e arquivos estáticos continuam disponíveis.
As telas mínimas abaixo são habilitadas junto ao módulo de contas. Sucesso em
POST usa redirecionamento 303 e mensagem; erro preserva somente campos seguros.
Não há API JSON para contas. Mariana mantém a responsabilidade pelo acabamento
visual; os novos templates mínimos não alteram `base.html` ou os arquivos estáticos.

| Caminho | Método | Campos do formulário (além de `csrf_token`) | Resultado |
| --- | --- | --- | --- |
| `/login` | GET/POST | `identificador`, `senha` | Tela; sucesso redireciona para `/sessao` |
| `/sessao` | GET | — | Tela com visão da conta autenticada |
| `/logout` | POST | — | Limpa o cookie e redireciona para login |
| `/contas/secretarios` | GET/POST | `nome`, `identificador`, `senha`, `confirmacao_senha` | Lista/cadastro, somente administrador |
| `/contas/secretarios/<id>/editar` | GET/POST | `nome`, `identificador` | Edição, somente administrador |
| `/contas/secretarios/<id>/situacao` | POST | `ativa`: `true` ou `false` | Reativação/desativação |
| `/contas/secretarios/<id>/senha` | POST | `senha`, `confirmacao_senha` | Redefinição de senha |

Senhas são confirmadas nos formulários de criação/reset. Templates recebem
projeções explícitas, nunca credenciais, hashes ou versão interna. Nome/e-mail
reaparecem em validação; campos de senha ficam vazios. Jinja escapa os valores.
O CSRF é campo oculto por sessão, rotacionado no login; mutações via GET são
recusadas. Campos extras/duplicados e arquivos são rejeitados. Corpo máximo 16 KiB.

Sessão assinada nativa do Flask mantém `conta_id`, `versao_sessao`, `expira_em`
e CSRF, sem senha ou perfil. Cookie HttpOnly/SameSite=Lax; Secure em HTTPS.
Em cada requisição do módulo, o backend verifica expiração absoluta (30 minutos),
conta ativa e contador igual. Reset/desativação/reativação/mudança de e-mail
invalidam cookies anteriores. Logout limpa somente o cookie do navegador atual;
não há registro por sessão ou garantia de revogar uma cópia roubada do cookie.
Esse limite é documentado para o escopo acadêmico local.

Sem login, páginas protegidas redirecionam para `/login` (302). Erros são HTML:
400 validação, 401 login inválido, 403 perfil/CSRF, 404 secretário inexistente,
409 e-mail duplicado, 413 corpo excessivo, 415 conteúdo sem formulário, 503
persistência com mensagem genérica. Respostas do módulo usam `no-store`.

**Ocorrências continuam futuras, sem rotas registradas:**

| Fluxo | Caminho/método proposto | Dependências |
| --- | --- | --- |
| Listar/detalhar | `GET /ocorrencias`, `GET /ocorrencias/<id>` | Campos públicos, filtros, ordem/paginação |
| Cadastrar | `GET/POST /ocorrencias/nova` | Modelo, campos e validações |
| Editar/excluir | `POST /ocorrencias/<id>/editar`, `POST /ocorrencias/<id>/excluir` | Serviço, SECRETARIO e política de exclusão |
| Status | `POST /ocorrencias/<id>/status` | Confirmação/cancelamento e transições |
| Vínculo | `POST /ocorrencias/vinculos` | Política P05 e serviço |

Esses fluxos aguardam os responsáveis e decisões P01–P08, com proteção no backend.
[Guia de validação e migração](desenvolvimento-luis.md).

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
