# Pendências e propostas para revisão da equipe

**Estado em 21/10/2026:** o solicitante selecionou alternativas para P01, P02, P03,
P04, P05, P06 e P09. **Essas seleções não equivalem à aprovação coletiva.**
Este documento registra o encaminhamento escolhido e as lacunas restantes,
sem alterar as regras já aprovadas em [regras-negocio.md](regras-negocio.md).
Não implementar como decisão final antes do alinhamento com a equipe.

**Convenção:** "seleção do solicitante" = proposta a submeter à equipe;
"aprovado anteriormente" = regra já consolidada; "a definir" = decisão
ainda aberta. Responsáveis indicados são sugestões de revisão, não
aceites individuais.

## Resumo das seleções (aguardando alinhamento)

| ID | Seleção informada | O que continua aberto |
| --- | --- | --- |
| P01 | **Revisar** campos e categorias do Figma | Todos os campos, categorias, anexos e exposição pública |
| P02 | Indexar **data da perda/achado** na AVL | Datas ausentes/aproximadas, hora, critérios de intervalo e desempate |
| P03 | Usar pesos e limiar apresentados como **configuração inicial de testes** | Normalização, evidência mínima, calibragem e aprovação para produção |
| P04 | Preferir **exclusão física** | Efeitos em vínculos, fotos, índice, persistência e eventuais trilhas |
| P05 | Preferir **vínculo 1:1, realizado por secretário** | Desvinculação, substituição, cancelamento/exclusão e integridade |
| P06 | Preferir **justificativa obrigatória ao cancelar** | Motivos, apresentação, persistência e propagação em pares |
| P09 | Administração com **cadastro, edição, desativação e redefinição de senha** | Identificação, recuperação, sessões, campos e política de segurança |

Os itens P07, P08, P10, P11 e P12 permanecem pendências técnicas e de
integração. O Figma é referência de comportamento da interface, **não**
evidência de que o código funciona nem aprovação automática de regras.

## Propostas já apresentadas à equipe

### P01 — Campos, categorias e exposição

**Seleção do solicitante:** **revisar campos e categorias**; nenhum
conjunto definitivo foi aprovado por essa seleção.

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
setor de guarda (inclusive a condição de ainda não entregue). Há foto
opcional e indicação visual de limite de 1,5 MB. O cadastro deve ser
curto, claro e funcionar sem conta pública.

**Ainda a decidir:** lista final de categorias, categoria única/múltipla,
campos mínimos de cada tipo, precisão/localização, data aproximada,
contato e exposição pública, cor, extensão/tamanho da descrição, formato
de imagens/anexos, limites e validações, necessidade e conteúdo dos dados
para conferência presencial. **Local de perda/achado e local de guarda
são campos distintos por regra já aprovada**. A seleção não autoriza
implementar os elementos do Figma como obrigatórios sem revisão.

**Bloqueia:** modelo completo, formulários reais, DTOs, codec definitivo
e correspondências que dependam desses atributos.
**Revisão:** equipe; Marcelo (modelo), Mariana (interface) e Matheus (JSON).

### P02 — Datas e índice temporal

**Seleção do solicitante:** utilizar na AVL a **data da perda para
registros PERDIDO e a data do achado para registros ENCONTRADO**, e
não a data do cadastro. A seleção está **pendente de aprovação da equipe**.

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

### P04 — Exclusão física ou lógica

**Seleção do solicitante:** preferir **exclusão física**, sujeita a
alinhamento da equipe. Isso significaria retirar definitivamente a
ocorrência da Lista e do JSON, atualizar a AVL e não exibi-la em buscas.

**Ainda a decidir:** impacto sobre ocorrência vinculada (não criar
referência órfã), exclusão ou retenção de imagens, política de
confirmação e permissões, eventual necessidade de trilha mínima de
auditoria/retensão e comportamento em falha durante a gravação.
A modal de confirmação do Figma demonstra a ação, mas não decide
sozinha os efeitos sobre dados.

**Bloqueia:** operação real de `excluir`, testes do ciclo completo
e integridade de vínculos/índice. **Revisão:** equipe; Marcelo, Matheus,
Leandro e Luís.

### P05 — Vínculos e transições

**Seleção do solicitante:** **um vínculo 1:1** entre um PERDIDO e um
ENCONTRADO, **feito por secretário autenticado**, podendo o secretário
atuar em qualquer bloco. A seleção está pendente de aprovação coletiva.

**Aprovado anteriormente:** sugerir correspondência não vincula nem
altera status automaticamente; após confirmação de devolução presencial,
as duas ocorrências vinculadas passam a RESOLVIDO; reabrir uma reabre
a outra. Não permitir dois parceiros para a mesma ocorrência se 1:1
for aprovado.

**Ainda a decidir:** ação e permissão para desfazer/substituir vínculo,
possibilidade de vincular antes da conferência presencial, elegibilidade
por status, vínculo de pares já encerrados, cancelamento e exclusão de
um parceiro, como manter histórico mínimo e comportamento atômico nas
mutações/JSON. Não confundir vínculo com conclusão da devolução.

**Bloqueia:** esquema de associação, rotas de vínculo, controle de
permissões e atualização conjunta. **Revisão:** equipe; Marcelo e Luís
com Matheus e André.

### P06 — Cancelamento

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

**Seleção do solicitante:** o administrador deverá **cadastrar, editar,
desativar e redefinir senhas** de contas de secretários. Essa lista de
operações requer aprovação da equipe; não inclui exclusão física de
contas nem autocadastro público. O Figma atual contempla o login da
secretaria, mas **não evidencia a tela completa de gestão de contas**.

**Aprovado anteriormente:** apenas administrador gerencia contas,
secretários não gerenciam contas nem ficam restritos a ocorrências do
próprio bloco; administrador não herda automaticamente ações de
secretário. A conta administrativa inicial é provisionada com segurança.

**Ainda a decidir:** identificador de login (o formulário do Figma
exibe e-mail institucional, ainda como referência), campos e unicidade,
desativação e bloqueio de sessões ativas, recuperação/redefinição
segura de senhas, ciclo de sessão, campos visíveis na administração,
proteção de credenciais e processo inicial. Não gerar login/senha padrão.

**Revisão:** Luís e equipe. **Bloqueia:** modelo definitivo de contas,
gestão administrativa, autenticação e rotas protegidas.

### P10 — Contrato HTTP e proteção antes das rotas

Fechar payloads, contextos Jinja, filtros, paginação, mensagens, redirects,
tratamento de erros e eventuais respostas JSON. Definir proteção CSRF para
POSTs, política de sessão e configuração HTTPS antes de expor mutações.
Não confundir ocultação de botão com autorização no backend.

**Comportamentos do Figma a detalhar no contrato, sem criar P13–P18:**
modal de escolha de tipo com fechar/voltar; navbar ativa sem repassar
cliques à tela; navegação e transições; busca por texto/código e filtros
combinados por tipo, categoria, local e setor; estados vazios; validação,
mensagens e confirmação do cadastro; explicação pública de status;
área da secretaria (todos os blocos e "meu setor"); conferência presencial,
cancelamento, exclusão, resolução e reabertura. Transições visuais não
comprovam que backend, dados ou autorização estejam implementados.

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

**Antes de converter seleções em requisitos:** registrar a validação coletiva
de P02, P04, P05, P06 e P09 e a configuração experimental de P03.
P01 continua em revisão aberta. Os desenvolvedores podem trabalhar com
mocks/testes parametrizados, mas não devem integrar comportamento definitivo
com base apenas nas seleções deste documento.

| Momento | Decisões | Trabalho paralelo que pode continuar |
| --- | --- | --- |
| Antes de modelo/formulários/codec finais | P01, P02, identidade em P12 | Lista, AVL, layout com fixtures, testes de cenários |
| Antes de persistência/mutações integradas | P04, P05, P07, P08 | Algoritmos, adaptadores isolados, autenticação com fakes |
| Antes de endpoints protegidos | P05, P06, P09, P10 | Templates, serviços testados isoladamente, CLI futura |
| Antes de matching final e entrega acadêmica | P03, P11, P12 | Integração progressiva dos fluxos já revisados |

Para registrar uma decisão, usar o ID Pxx, texto exato aprovado, data,
participantes e módulos impactados; atualizar regras/contratos no mesmo PR.
As seleções de 21/10/2026 permanecem **propostas para decisão da equipe**;
nenhuma delas foi promovida a regra aprovada por esta atualização.
