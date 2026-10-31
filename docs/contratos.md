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

## Alinhamento com SCRUM-8/9 — 31/10/2026

Por solicitação de Luís, contas passam a JSON e as regras conflitantes de
ocorrências seguem o [contrato de Marcelo](https://github.com/luis-sandri/PUCEncontrou/blob/03fb6fb23b5662587cada2c0b6caf263ef0d7303/docs/scrum-8.md).
Modelo, codec, lotes e núcleo estão disponíveis nessa branch; esta adequação
**não importa suas implementações** nem registra rotas de ocorrência.
O serviço protegido futuro deve envolver o núcleo, validar autorizações e
uploads e só então expor operações. A Lista manual e sua integração de produção
continuam com os respectivos responsáveis.

Campos mínimos do modelo de Marcelo: nome, categoria, data da ocorrência,
local e referência de foto, com foto obrigatória em ambos os tipos; descrição
e cor opcionais. Guarda é exclusiva de ENCONTRADO. Vínculo é 1:1 entre tipos
opostos abertos, com resolução/reabertura conjuntas. Exclusão física limpa o
vínculo no parceiro sem alterar seus demais dados/status. Cancelamento só de
ABERTO isolado; justificativa e propagação continuam pendentes.

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
- `ator` vem da autenticação do backend e da conta carregada no JSON de contas.
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
| Modelo concreto | Classe `Ocorrencia`, campos e validações | Disponível na branch SCRUM-8; não importada nesta adequação |

Assinaturas de codec/modelo implementadas na branch SCRUM-8; arquivo com Matheus:

```python
Ocorrencia.criar(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.corrigir(dados: Mapping[str, object]) -> Ocorrencia
ocorrencia.para_registro() -> dict[str, object]
Ocorrencia.de_registro(registro: Mapping[str, object]) -> Ocorrencia
```

O codec não deve gerar novo ID, forçar `ABERTO` ao recarregar, perder vínculos
ou confundir os dois locais. A criação não é um atalho para alterar status.
O protocolo de leitura continua mínimo. O modelo de Marcelo já define data,
descrição, categoria, cor, foto, guarda e vínculos conforme o guia SCRUM-8.
Dados de contato e exposição pública seguem em revisão. Validação não deve
ser distribuída em seis versões incompatíveis.

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
- `vincular` não confirma devolução nem altera status automaticamente. A
  autorização de secretário deve ser validada no serviço protegido, conforme
  o desenho SCRUM-8; o núcleo interno não pode ser exposto diretamente.
- `excluir` segue exclusão física e limpa o vínculo no parceiro sem alterar
  seus demais dados/status. Integração com Lista/AVL/JSON e fotos continua pendente.

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

## Contas JSON e autenticação — Luís

Contrato alinhado à persistência de SCRUM-8 em 31/10. As escolhas de nome,
e-mail, gestão e sessão de P09/P10 permanecem iguais. `ContaAdministrativa` e
`CredenciaisConta` são imutáveis. Visão e `ContaAdministrativaPorta`: `id: str`,
`perfil: Perfil`, `nome: str`, `identificador: str`, `ativa: bool` e contador
interno `versao_sessao: int`. Credenciais acrescentam `senha_hash: str` (fora do
repr) e `para_visao() -> ContaAdministrativa`. Templates recebem somente os
cinco campos administrativos, sem hash ou contador.

Código: protocolo em `app/repositories/contas.py`, concreto
`RepositorioContasJSON(caminho: Path | str)` em `app/repositories/json_contas.py`.
O construtor não faz I/O. O protocolo oferece:

```python
inicializar() -> None
inicializar_administrador(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativa
buscar_por_id(conta_id: str) -> CredenciaisContaPorta | None
buscar_por_identificador(identificador: str) -> CredenciaisContaPorta | None
salvar_secretario(dados: Mapping[str, object], *, senha_hash: str) -> ContaAdministrativaPorta
listar_secretarios() -> list[ContaAdministrativa]
atualizar_secretario(conta_id: str, dados: Mapping[str, object], *, senha_hash: str | None = None) -> ContaAdministrativa
recuperar_administrador(identificador: str, *, senha_hash: str) -> ContaAdministrativa
importar_legado_sqlite(origem: Path | str) -> int
```

O concreto devolve `CredenciaisConta`/`ContaAdministrativa` onde a porta descreve
essas visões. Arquivo UTF-8 separado das ocorrências, com envelope
`{"versao": 1, "contas": [...]}`. Cada registro contém somente os seis campos da
conta e `senha_hash`; perfil como texto. IDs UUID e e-mails normalizados são
únicos; no máximo um administrador inicial. Arquivo ausente, inválido, registros
inconsistentes ou versão desconhecida geram `ErroPersistencia`, sem substituição
silenciosa por vazio. A inicialização explícita cria arquivo vazio ou valida o
existente sem regravá-lo. Consulta/fábrica não criam arquivos.

Escritas geram snapshot em temporário no mesmo diretório e usam `os.replace`.
Senha/situação/e-mail e contador são gravados juntos; falha preserva o arquivo
anterior. Lock coordena requisições da mesma instância. Usar **um processo por
arquivo** e executar CLI com servidor parado; não há coordenação entre processos.
O adaptador não mantém cache. Seu JSON de contas não define nem implementa o
arquivo de ocorrências de Matheus, a Lista manual ou a AVL.

```python
# ServicoContas(repositorio: RepositorioContasPorta)
listar_secretarios(*, ator: ContaAdministrativaPorta) -> list[ContaAdministrativa]
obter_secretario(conta_id: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativa
cadastrar_secretario(dados: Mapping[str, object], senha: str, *, ator: ContaAdministrativaPorta) -> ContaAdministrativa
gerenciar_secretario(conta_id: str, alteracoes: Mapping[str, object], *, ator: ContaAdministrativaPorta) -> ContaAdministrativa

# ServicoAutenticacao(repositorio: RepositorioContasPorta)
autenticar(identificador: str, senha: str) -> ContaAdministrativa
obter_sessao(conta_id: str, versao_sessao: int) -> ContaAdministrativa | None
preparar_arquivo() -> None
inicializar_administrador(dados: Mapping[str, object], senha: str) -> ContaAdministrativa
recuperar_administrador(identificador: str, senha: str) -> ContaAdministrativa
importar_contas_legadas(origem: str) -> int
```

As portas dos serviços mantêm retornos `ContaAdministrativaPorta`;
`GestaoContasPorta.listar_secretarios` usa `Sequence[ContaAdministrativaPorta]`.
Preparação, bootstrap, recuperação e importação são exclusivos da CLI local.
O antigo `atualizar_banco()` foi substituído por `preparar_arquivo()`;
configuração agora é `CONTAS_JSON` / `PUC_CONTAS_JSON`, padrão
`instance/contas.json`. `CONTAS_SQLITE` não é mais usado pelo aplicativo.

Importação abre o SQLite legado v1/v2 somente para leitura, preserva IDs,
hashes, nomes, identificadores e situação, e grava um JSON novo. Recusa destino
existente, fonte incompatível ou registros inválidos. Não altera/apaga a origem.
Para login genérico legado, ajustar e-mail pela recuperação local ou edição de
secretário. Não há migração automática durante requisições.

Gestão exige administrador ativo recarregado pelo ID. Só modifica secretários;
não confia em perfil recebido. Campos permitidos: `nome`, `identificador`,
`ativa: bool` e/ou `senha`; não há exclusão, gestão pública de administradores
ou alteração de credenciais próprias. Mudança de e-mail, situação ou senha
incrementa o contador junto aos dados; renomear preserva a versão.

Nome tem 1–120 caracteres após `strip`, sem controles. E-mail institucional
`@pucpr.edu.br` tem até 120 caracteres e é normalizado com `strip`/`casefold`.
Senha tem 12–128 caracteres Unicode válidos, sem normalização; hash/verificação
Werkzeug. Falha de login é genérica. Nenhuma senha em texto vai para arquivo,
DTO, template ou log. Limites técnicos continuam sujeitos à revisão da equipe.

`CONTAS_HABILITADAS` / `PUC_CONTAS_HABILITADAS=true` permanece falso por padrão.
Quando habilitado, a fábrica compõe serviços em `app.extensions['autenticacao']`
e `['contas']`, sem instanciar protocolos ou criar dados. Duração de sessão
configurada por `CONTAS_DURACAO_SESSAO_SEGUNDOS`, inteiro positivo, padrão 1800.

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
