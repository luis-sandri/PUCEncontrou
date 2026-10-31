# Pendências e propostas para revisão da equipe

**Estado em 31/10/2026:** Luís solicitou adaptar somente os pontos conflitantes
às regras registradas nas branches de Marcelo. **Contas passam de SQLite para
JSON**, e a documentação incorpora foto obrigatória, campos mínimos e o
comportamento de exclusão/vínculos do registro SCRUM-8. A fonte é a
[branch revisada](https://github.com/luis-sandri/PUCEncontrou/blob/03fb6fb23b5662587cada2c0b6caf263ef0d7303/docs/regras-negocio.md), com decisões de 19/10 e desenho de 27/10.
Esta solicitação não acrescenta aprovação coletiva inexistente.

As definições de Luís de 30/10 para P09/P10 permanecem: e-mail `@pucpr.edu.br`,
gestão de secretários, sessão de 30 minutos e formulários Jinja. O módulo usa
agora JSON e pode importar explicitamente o legado SQLite sem alterá-lo.
Modelo, núcleo e Lista dos colegas **continuam em suas branches**, sem serem
incorporados por esta adequação. O acabamento com Mariana e a integração de
ocorrências continuam separados. Veja [regras](regras-negocio.md),
[contratos](contratos.md) e [guia de validação](desenvolvimento-luis.md).

**Convenção:** "seleção do solicitante" = proposta a submeter à equipe;
"aprovado anteriormente" = regra já consolidada; "a definir" = decisão
ainda aberta. Responsáveis indicados são sugestões de revisão, não
aceites individuais.

## Resumo das seleções (aguardando alinhamento)

| ID | Seleção informada | O que continua aberto |
| --- | --- | --- |
| P01 | Campos mínimos do desenho SCRUM-8 e **foto obrigatória nos dois tipos** | Categorias finais, uploads e exposição pública |
| P02 | Indexar **data da perda/achado** na AVL | Datas ausentes/aproximadas, hora, critérios de intervalo e desempate |
| P03 | Usar pesos e limiar apresentados como **configuração inicial de testes** | Normalização, evidência mínima, calibragem e aprovação para produção |
| P04 | **Exclusão física**, limpando o vínculo no parceiro e preservando seus dados/status | Remoção de imagens, índice, persistência e eventual trilha |
| P05 | **Vínculo 1:1 entre tipos opostos abertos**, confirmado por secretário no serviço protegido | Desvinculação/substituição e integração indivisível |
| P06 | Núcleo cancela somente **ABERTO sem vínculo**; justificativa obrigatória continua proposta | Justificativa e política de cancelamento de pares |
| P09 | **JSON alinhado em 31/10**; definido por Luís em 30/10: nome, e-mail `@pucpr.edu.br` único; cadastro, edição, desativação, reativação e reset; sessão de 30 minutos; recuperação local do administrador | Revisão coletiva e validação de uso |
| P10 | **Contas definidas por Luís em 30/10:** formulários Flask/Jinja, POST com redirecionamento, sessão Flask e proteções básicas | Acabamento visual com Mariana; contratos de ocorrências; revisão coletiva |

Os itens P07, P08, P11 e P12, além dos fluxos de ocorrências em P10, permanecem pendências técnicas e de
integração. O Figma é referência de comportamento da interface, **não**
evidência de que o código funciona nem aprovação automática de regras.

## Propostas já apresentadas à equipe

### P01 — Campos, categorias e exposição

**Alinhado com SCRUM-8 em 31/10:** nome, categoria, data da ocorrência, local
e foto são obrigatórios; descrição e cor são opcionais. Foto é obrigatória
em PERDIDO e ENCONTRADO, inclusive cadastro interno. Categorias continuam em
texto livre; a lista final e outras decisões de exposição não foram fechadas.

Categorias propostas anteriormente (continuam abertas):

- Eletrônicos e acessórios
- Materiais acadêmicos
- Documentos e cartões
- Garrafas e recipientes
- Roupas e acessórios
- Guarda-chuvas
- Bolsas e mochilas
- Outros

**Referência do Figma (não aprovada como contrato):** os formulários
separam PERDIDO/ENCONTRADO, identificam campos com `*`, incluem nome,
categoria, data, descrição e local da perda/achado. O achado também informa
setor de guarda (inclusive a condição de ainda não entregue). A referência
antiga de foto opcional foi superada por SCRUM-8. O limite visual de 1,5 MB
continua referência, sem validação de upload aprovada nesta adequação. O cadastro deve ser
curto, claro e funcionar sem conta pública.

**Ainda a decidir:** lista final de categorias, categoria única/múltipla,
detalhes adicionais de campos, precisão/localização, data aproximada,
contato e exposição pública, cor, extensão/tamanho da descrição, formato
de imagens/anexos, limites e validações, necessidade e conteúdo dos dados
para conferência presencial. **Local de perda/achado e local de guarda
são campos distintos por regra já aprovada**. A seleção não autoriza
implementar os elementos do Figma como obrigatórios sem revisão.

**Ainda bloqueia:** integração dos formulários, uploads, DTOs públicos e
correspondência. O modelo e codec mínimos já estão na branch SCRUM-8.
**Revisão:** equipe; Marcelo (modelo), Mariana (interface) e Matheus (JSON).

### P02 — Datas e índice temporal

**Seleção do solicitante:** utilizar na AVL a **data da perda para
registros PERDIDO e a data do achado para registros ENCONTRADO**, e
não a data do cadastro. O modelo SCRUM-8 já usa `data_ocorrencia: date`
obrigatória. Integração, fronteiras e tratamento de datas aproximadas ainda
precisam de revisão com Leandro.

**Referência de IHC:** a secretaria apresenta também data de recebimento
pelo setor e tempo de guarda. São informações diferentes da data do
achado e não devem substituí-la silenciosamente no índice.

**Ainda a decidir:** como lidar com data aproximada, inválida ou
ausente; se haverá horário, precisão e fuso; filtros por período e
fronteiras inclusivas; desempate e múltiplos registros na mesma data;
atualização do índice quando data for editada; como calcular tempo de
guarda sem presumir data de recebimento. IDs opacos e chave composta
`(data, id)` permanecem sugestões técnicas, não decisões definitivas.

**Bloqueia:** extrator de data, consultas reais e sincronização após edição.
**Revisão:** Leandro, Marcelo, Matheus e Luís. A AVL pode avançar com
pares sintéticos antes da aprovação.

### P03 — Política de correspondência

**Seleção do solicitante:** adotar **somente como configuração inicial
para testes** a proposta já discutida: categoria 30, cor 20,
local da perda/achado 20, proximidade de data 20, termos da descrição
10 pontos; mostrar até 5 candidatos e usar limiar inicial 60/100.
**Não é limiar validado, nem regra final de produção.**

**Regras já aprovadas:** algoritmo determinístico, sem IA; apenas
sugestões PERDIDO ↔ ENCONTRADO, sem confirmar propriedade ou alterar
status. O setor de guarda não deve ser usado como substituto do local
da perda/achado na comparação.

**Ainda a decidir/testar:** dados ausentes, normalização sem pontuação
artificialmente alta, evidência mínima comparável, janela temporal,
critérios para variações de categoria, análise de termos, desempate,
exclusão de ocorrências encerradas/vinculadas, apresentação do motivo
da sugestão, cenários de falsos positivos e métricas para recalibrar
pesos e limiar. Exemplo de cuidado: categoria isolada não deve gerar
correspondência forte por normalização indevida.

**Bloqueia:** pontuação definitiva, contrato dos resultados e testes de
qualidade do matching. **Revisão:** André com equipe. Pode começar
com parâmetros alteráveis e fixtures sintéticas, identificados
explicitamente como experimento.

### P04 — Exclusão física

**Alinhado com o desenho SCRUM-8:** exclusão física. Quando há vínculo,
remover o registro e limpar a referência no parceiro, preservando seus demais
dados e status. A escolha foi registrada por Marcelo em 27/10 e adotada por
Luís para conciliar esta branch em 31/10.

**Ainda a decidir/integrar:** descarte das fotos físicas, atualização da Lista,
AVL e JSON, confirmação, falhas de gravação e eventual trilha. O núcleo prepara
o lote, mas não remove imagens nem implementa a persistência de produção.
Revisão: Marcelo, Matheus, Leandro e Luís.

### P05 — Vínculos e transições

**Alinhado com SCRUM-8:** vínculo 1:1 entre um PERDIDO e um ENCONTRADO, ambos
ABERTO e sem parceiro. Vínculo não resolve automaticamente. A ação pertence
ao secretário autenticado, sem restrição por bloco, validada no serviço de
SCRUM-16 antes de usar o núcleo interno.

Resolução após conferência presencial e reabertura atingem os dois parceiros.
Cancelamento de par fica bloqueado enquanto não houver política. A exclusão
segue P04 e preserva o parceiro sem referência órfã.

**Ainda aberto:** desfazer/substituir vínculo como ação autônoma, política de
cancelamento de pares e integração indivisível com Lista/AVL/JSON. O núcleo
prepara lotes; não fornece autorização ou persistência de produção.
Revisão: Marcelo, Luís, Matheus e André.

### P06 — Cancelamento

**Alinhado com o núcleo SCRUM-8:** cancelar somente ABERTO isolado. Cancelamento
de ocorrência vinculada é bloqueado enquanto a propagação não estiver definida.
Isso não resolve ainda a proposta de justificativa abaixo.

**Seleção do solicitante:** exigir **justificativa obrigatória** quando
secretário mudar a situação para CANCELADO; decisão ainda não ratificada
pela equipe.

**Aprovado anteriormente:** existem ABERTO, RESOLVIDO e CANCELADO;
secretários gerenciam situação, com reabertura possível nos termos
já definidos para ocorrências vinculadas.

**Ainda a decidir:** motivos pré-definidos ou texto livre, tamanho e
validação da justificativa, quem poderá visualizá-la, registro no JSON,
qual transição pode cancelar ou reabrir, propagação de cancelamento ao
par e diferença entre cancelamento e exclusão física. O Figma fornece
um fluxo de cancelamento, mas não resolve todas essas regras.

**Bloqueia:** mutações finais e testes de cancelamento/reabertura.
**Revisão:** equipe; Marcelo, Luís e Mariana.

## Pendências técnicas e de integração identificadas nesta preparação

### P07 — Schema JSON, codec e tratamento de arquivo

**Alinhamento em 31/10:** ocorrências e contas ficam em arquivos JSON locais
separados. O codec de ocorrências está na branch SCRUM-8; o arquivo de ocorrências
continua com Matheus. O JSON de contas é mantido por Luís, com envelope v1 e
importação explícita do legado SQLite; não define o esquema de ocorrências.

Revisar envelope versionado ou formato simples, tipos de ID/data, validação
do snapshot, arquivo inexistente, migração, backup e recuperação de dados.
Proposta: UTF-8, codec do domínio, erro explícito em arquivo corrompido e
escrita por snapshot; não apagar dados diante de falha de leitura.

Revisão: Matheus e Marcelo; Leandro revisa reconstrução e Luís configuração.
Parte dos trabalhos pode usar codec fake sem depender de P01 final.

### P08 — Coerência, concorrência e falhas

Contas usam leitura por operação e substituição atômica de snapshot JSON, com
lock entre requisições da mesma instância. Usar um processo por arquivo e CLI
com servidor parado. A coerência Lista/AVL/JSON de ocorrências abaixo continua
na integração SCRUM-13; não foi implementada nesta adequação.

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

**Definido com Luís em 30/10, com persistência alinhada em 31/10 para JSON.**
Nome, e-mail institucional, gestão e sessão permanecem iguais. SQLite foi
retirado do funcionamento normal; a CLI pode importar contas antigas em modo
somente leitura, sem substituir um JSON existente ou apagar o legado.

| Tema | Seleção de Luís e comportamento implementado |
| --- | --- |
| Persistência | JSON local separado das ocorrências, responsabilidade de Luís |
| Login | E-mail institucional **`@pucpr.edu.br`**, confirmado expressamente por Luís |
| Dados | Nome e e-mail; ID gerado pelo backend, sem bloco obrigatório |
| Unicidade | E-mail único, removendo espaços externos e ignorando maiúsculas/minúsculas |
| Gestão | Administrador lista, cadastra, edita nome/e-mail, desativa, reativa e redefine senhas de secretários |
| Permissões | Secretário não gerencia contas; administrador não herda ações de secretário |
| Desativação | Impede login e invalida sessões existentes; reativação exige novo login |
| Redefinição | Administrador confere a identidade antes de definir uma nova senha; sessões anteriores deixam de valer |
| Sessão | Cookie assinado do Flask, duração absoluta de 30 minutos e consulta da conta ativa no backend |
| Administrador inicial | CLI local com senha oculta e confirmação, sem senha padrão ou cadastro público |
| Recuperação do administrador | CLI local explícita, preservando a conta e redefinindo seu e-mail/senha |
| Senhas | Hash Werkzeug; limite técnico de 12–128 caracteres Unicode válidos, sem normalização |

Não fazem parte deste escopo: exclusão física de contas, criação de novos
administradores, recuperação por e-mail ou alteração de credenciais próprias.
A conta mantém apenas um contador para invalidar acessos após mudanças de
credenciais/situação; não existe mais tabela de sessões.

**O que falta:** Luís validar os fluxos e a equipe revisar essas escolhas antes
da integração final. O acabamento dos formulários deve ser alinhado com Mariana.
Não há dúvida de domínio de e-mail, reativação ou duração de sessão pendente
para implementar a versão atual. Revisão da equipe não impede o teste local.

### P10 — Contrato HTTP e proteção antes das rotas

**Escopo de contas definido com Luís em 30/10/2026 e aplicado ao código:**

- Formulários HTML renderizados pelo Flask/Jinja; sucesso em POST redireciona
  com mensagem, erro reexibe campos seguros e nunca a senha.
- Login/logout e administração usam cookie de sessão do Flask; conta ativa e
  perfil são verificados no backend. Sessões expiram em 30 minutos.
- Hash de senha, persistência JSON validada, campos permitidos explícitos e CSRF em
  formulários que alteram dados são as proteções básicas mantidas.
- A API JSON e a tabela de sessões do primeiro protótipo foram retiradas.
- Limitação de tentativas, recuperação automática por e-mail e infraestrutura
  de publicação não são requisitos desta entrega acadêmica local. Se houver
  publicação posterior, configuração HTTPS/cookie Secure deve ser revisada.

**Implementado para avaliar:** telas mínimas de login, sessão, listagem,
cadastro, edição, ativação/desativação e reset. Não são reprodução final do
Figma. Mariana continua responsável pela integração visual.

**Permanece aberto para ocorrências:** campos públicos/privados, filtros,
paginação, contextos Jinja, mensagens e confirmações; integração das regras de
status/vínculo após as decisões de P01–P08 e os serviços dos responsáveis.

Os comportamentos de referência do Figma continuam para detalhar com os
responsáveis: escolha PERDIDO/ENCONTRADO, navegação, busca/filtros combinados,
estados vazios, validação e confirmação de cadastro, explicação de status,
área da secretaria, conferência presencial, cancelamento, exclusão e reabertura.
Eles não demonstram implementação nem aprovação automática de regras.

**O que falta:** revisão dos formulários com Mariana e dos fluxos de ocorrência
com a equipe; André participa da integração. P10 não bloqueia mais o teste do
módulo de contas. [Contratos](contratos.md) descrevem os caminhos e campos atuais.

### P11 — Rubrica e detalhes das estruturas manuais

A Lista manual está implementada na branch SCRUM-9: buffer fixo, capacidade
padrão 4, expansão por duplicação e cópia/deslocamento manuais. A AVL está na
branch de Leandro. Esta adequação não copia nem altera essas implementações.

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

**Antes de converter seleções em requisitos:** registrar a validação coletiva
dos pontos ainda abertos em P02, P06 e P09 e a configuração experimental de P03.
P04/P05 seguem agora os comportamentos registrados no desenho SCRUM-8.
P01 continua em revisão aberta. Os desenvolvedores podem trabalhar com
mocks/testes parametrizados, mas não devem integrar comportamento definitivo
com base apenas nas seleções deste documento.

| Momento | Decisões | Trabalho paralelo que pode continuar |
| --- | --- | --- |
| Antes de modelo/formulários/codec finais | P01, P02, identidade em P12 | Lista, AVL, layout com fixtures, testes de cenários |
| Antes de persistência/mutações integradas | P04, P05, P07, P08 | Algoritmos, adaptadores isolados, autenticação com fakes |
| Antes de integrar rotas protegidas de ocorrências | P05, P06 e parte de ocorrências de P10 | Contas já podem ser testadas; P09/P10 de contas definidos por Luís aguardam revisão coletiva |
| Antes de matching final e entrega acadêmica | P03, P11, P12 | Integração progressiva dos fluxos já revisados |

Para registrar uma decisão, usar o ID Pxx, texto exato aprovado, data,
participantes e módulos impactados; atualizar regras/contratos no mesmo PR.
As seleções de 21/10 permanecem propostas coletivas. Em 30/10, Luís detalhou
P09/P10 para sua branch. Em 31/10, pediu adoção das regras conflitantes de
SCRUM-8/9 conforme as fontes acima. Não foram inventados participantes, reuniões
ou novas aprovações dos demais integrantes.
