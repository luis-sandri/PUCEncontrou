# Pendências e propostas sem aprovação

Nada nesta página é uma regra aprovada. O campo "responsáveis pela revisão"
orienta a conversa; não registra decisão nem delegação já aceita pelos colegas.
Registrar aqui a decisão real, data e participantes quando a equipe revisar.

## Propostas já apresentadas à equipe

### P01 — Campos, categorias e exposição

Categorias propostas:

- Eletrônicos e acessórios
- Materiais acadêmicos
- Documentos e cartões
- Garrafas e recipientes
- Roupas e acessórios
- Guarda-chuvas
- Bolsas e mochilas
- Outros

Faltam os campos obrigatórios/opcionais exatos, limites de tamanho, cor,
descrição, identificação de bloco/local, contato e sua exposição pública,
categoria única/múltipla e necessidade de anexos. Não incluir upload ou
campos como requisito sem decisão. Os dois tipos de local já são distintos
por regra aprovada, mas representação e obrigatoriedade não estão definidas.

Bloqueia: modelo completo, formulários, DTOs, codec definitivo e matching.
Revisão: equipe; Marcelo coordena modelo, Mariana interface, Matheus JSON.

### P02 — Datas e índice temporal

Qual data será indexada: perda/achado ou cadastro? `date` basta ou há hora?
O que fazer quando a data não estiver disponível? Qual timezone para
conversões? Qual limite inclusivo/exclusivo e ordem de empate desejados?
Uma ocorrência pode ter mais de uma data consultável?

IDs opacos em string, limites inclusivos e desempate não especificado são
convenções técnicas v0 propostas, não decisões de produto. A AVL pode ser
desenvolvida com pares sintéticos antes de escolher o campo do modelo.

Bloqueia: extrator de data, consulta real e sincronização após edição.
Revisão: Leandro, Marcelo, Matheus e Luís.

### P03 — Política de correspondência

Proposta existente: categoria 30, cor 20, local 20, proximidade temporal 20,
descrição 10; até 5 candidatos, limiar inicial 60/100.

Faltam tratamento de valores ausentes, normalização, janela temporal,
comparação de descrição/local, desempates, status elegíveis, tipos elegíveis,
vínculos existentes, explicação dos resultados e critério para validar o limiar.
Não assumir que campo ausente vale zero nem redistribuir pesos sem decisão.
O total 100 é apenas a soma proposta; não valida eficácia da regra.

Bloqueia: matching pontuado final, campos de resultado e testes de expectativa.
Revisão: André e equipe. Pode preparar política parametrizável e cenários,
sem IA, sem confirmar propriedade e sem mudar status (restrições já aprovadas).

### P04 — Exclusão física ou lógica

Decidir retenção, visibilidade pública, possibilidade de restauração,
representação no JSON, efeito na AVL, histórico e comportamento do vínculo.
Não criar `excluido`, `deleted_at` ou apagar arquivos como decisão implícita.

Bloqueia: implementação de `excluir` e testes de consultas após exclusão.
Revisão: equipe; Marcelo, Matheus, Leandro e Luís avaliam impacto.

### P05 — Vínculos e transições não especificadas

Está aprovado que um par PERDIDO/ENCONTRADO pode ser vinculado, que resolução
após confirmação afeta ambos e que reabertura de um afeta ambos.

Faltam quem vincula/desvincula, cardinalidade, substituição de vínculo,
status permitidos ao vincular, representação, efeitos de cancelamento/exclusão
e transições adicionais. Não presumir um ID único de parceiro, múltiplos
parceiros, criação pública ou resolução automática ao vincular.

Bloqueia: schema de vínculos, endpoint, autorização e mutações relacionadas.
Revisão: equipe; Marcelo e Luís coordenam com Matheus e André.

### P06 — Cancelamento

Motivos, obrigatoriedade de justificativa, campos, visibilidade e transições
de/para `CANCELADO` não foram aprovados. Propagação em pares também não foi
definida. Não transformar uma lista de motivos em enum definitivo.

Bloqueia: contexto final de cancelamento e testes dessas transições.
Revisão: equipe; Marcelo, Luís e Mariana avaliam implementação.

## Pendências técnicas e de integração identificadas nesta preparação

### P07 — Schema JSON, codec e tratamento de arquivo

Revisar envelope versionado ou formato simples, tipos de ID/data, validação
do snapshot, arquivo inexistente, migração, backup e recuperação de dados.
Proposta: UTF-8, codec do domínio, erro explícito em arquivo corrompido e
escrita por snapshot; não apagar dados diante de falha de leitura.

Revisão: Matheus e Marcelo; Leandro revisa reconstrução e Luís configuração.
Parte dos trabalhos pode usar codec fake sem depender de P01 final.

### P08 — Coerência, concorrência e falhas

Definir a estratégia para que Lista, AVL e JSON permaneçam coerentes após
falha de escrita e mutação de dois registros. Proposta: preparar alteração,
gravar snapshot atomicamente e publicar/confirmar estado com lock e rollback
ou mecanismo equivalente. A sequência concreta precisa de testes.

Para a primeira implantação, propõe-se um processo e coordenação de leitura/
escrita em serviço. Vários workers exigem solução adicional; não assumir
sincronização só por usar JSON e `os.replace`.

Revisão: Luís, Matheus, Marcelo, Leandro e André. Bloqueia integração segura
de mutações reais, sem bloquear os algoritmos isolados.

### P09 — Contas e alcance dos perfis

Definir identificador de login, campos e unicidade; quais ações "gerenciar"
inclui (edição, desativação, exclusão, reset); ciclo de sessão, recuperação
de acesso e rotina inicial segura. Não criar login/senha padrão.

Administrador tem responsabilidade aprovada de contas, sem herança automática
de poderes de secretário. Qualquer acúmulo de funções requer confirmação.
Não ampliar automaticamente gestão para outros administradores.

Revisão: Luís e equipe. Bloqueia schema completo, gestão e rotas protegidas.

### P10 — Contrato HTTP e proteção antes das rotas

Fechar payloads, contextos Jinja, filtros, paginação, mensagens, redirects,
tratamento de erros e eventuais respostas JSON. Definir proteção CSRF para
POSTs, política de sessão e configuração HTTPS antes de expor mutações.
Não confundir ocultação de botão com autorização no backend.

Revisão: Luís e Mariana; André valida a matriz no backend. Rascunhos de
rotas e convenções de erro estão em [contratos](contratos.md).

### P11 — Rubrica e detalhes das estruturas manuais

Confirmar com o professor a representação permitida do array, critérios
de demonstração/complexidade, capacidade inicial e política de crescimento.
Leandro define duplicatas e rotações na AVL; consultas temporais devem usar
o índice de produção. Auxiliar de IDs não substitui a Lista ou a AVL.

Revisão: Marcelo, Leandro e equipe. Protocolos/fakes não cumprem a implementação.

### P12 — Versões e aceitação dos contratos

Revisar o Python mínimo da equipe, fixação de dependências para a entrega,
assinaturas v0, erros e responsabilidades de revisão. A base recomenda
Python 3.12 e faixas compatíveis; não há lockfile de entrega definitivo.

Revisão: todos, com coordenação de Luís. Pode haver PRs de módulo antes da
fixação, mas mudanças incompatíveis devem atualizar consumidores juntos.

## Prioridade para liberar a integração

| Momento | Decisões | Trabalho paralelo que pode continuar |
| --- | --- | --- |
| Antes de modelo/formulários/codec finais | P01, P02, identidade em P12 | Lista, AVL, layout com fixtures, testes de cenários |
| Antes de persistência/mutações integradas | P04, P05, P07, P08 | Algoritmos, adaptadores isolados, autenticação com fakes |
| Antes de endpoints protegidos | P05, P06, P09, P10 | Templates, serviços testados isoladamente, CLI futura |
| Antes de matching final e entrega acadêmica | P03, P11, P12 | Integração progressiva dos fluxos já revisados |

Para registrar uma decisão, usar o ID Pxx, texto exato aprovado, data,
participantes e módulos impactados; atualizar regras/contratos no mesmo PR.
Nenhuma pendência foi marcada como aprovada nesta preparação.
