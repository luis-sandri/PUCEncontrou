# SCRUM-8 — Modelo e núcleo CRUD de ocorrências

Data: 27/10/2026. Estado: aprovado por Marcelo nesta conversa ("Pode implementar").

## Objetivo e limites

Implementar a primeira tarefa de Marcelo: modelo concreto, operações CRUD e
transições testáveis, seguindo Python/Flask, nomes em português, tipagem e
camadas existentes. A Lista manual será a etapa seguinte (SCRUM-9).
Não implementar contas, upload, rotas, algoritmo de correspondência, AVL,
repositório JSON ou sincronização de produção pertencentes às outras tarefas.
Não alterar Jira, publicar, fazer commit ou push automaticamente.

As decisões trazidas pelo usuário prevalecem: foto obrigatória em ambos os
tipos; ocorrências e contas em JSON local; imagens em arquivos locais.
Exclusão física foi escolhida por Marcelo nesta conversa em 27/10/2026.
Documentação antiga divergente será identificada e corrigida no escopo dos
contratos afetados, sem implementar o módulo de contas.

## Abordagens consideradas

1. Modelo independente e núcleo CRUD por dependências injetadas, usando fakes
   de armazenamento nos testes. Recomendado: permite entregar SCRUM-8 antes de
   SCRUM-9 sem substituir a Lista acadêmica ou concluir módulos dos colegas.
2. Implementar modelo, Lista, AVL, JSON e rotas juntos. Facilita uma demonstração
   ponta a ponta, mas mistura tarefas e responsabilidades; descartado pelo
   pedido de executar uma parte por vez.

A abordagem 1 foi aprovada pelo usuário para esta implementação.

## Modelo proposto

Ocorrencia será um objeto imutável; edição produz outro objeto com o mesmo ID.
UUID textual gerado no backend na criação; recarga preserva ID, status e vínculo.
Os enums existentes PERDIDO/ENCONTRADO e ABERTO/RESOLVIDO/CANCELADO permanecem.
Campos: categoria, nome, descrição, cor, data da ocorrência, local da ocorrência,
referência da foto, setor de guarda, data de recebimento, destinação a verificar
e ID da ocorrência vinculada. Datas de calendário usam datetime.date; o codec
converte para/de ISO sem ler ou gravar arquivos.

Foto exige referência local não vazia em toda construção e correção. O modelo
não acessa disco. A verificação de recebimento real e correspondência do arquivo
é dependência obrigatória dos serviços de SCRUM-16; não simular essa garantia
com um caminho não vazio nem habilitar rotas antes dessa integração.

Categorias não terão enum fechado enquanto a lista final estiver pendente.
Proposta provisória: nome, categoria, data e local preenchidos; descrição e cor
podem estar ausentes. Estas escolhas provisórias foram aprovadas pelo
solicitante para a implementação, sem registrar aprovação coletiva fictícia.

Em ENCONTRADO, guarda distingue setor informado de AINDA_NAO_ENTREGUE, sem usar
local da ocorrência como substituto. Recebimento pode ser ausente e nunca será
inferido da data do achado. PERDIDO não recebe campos exclusivos de guarda.
Destinação a verificar registra informação, sem autorizar ou automatizar doação.

## Operações e integração

Núcleo interno de CRUD consulta uma porta de leitura e prepara lotes imutáveis
com versões anteriores e posteriores dos registros. Uma porta de aplicação de
lote confirma a alteração integralmente ou falha sem publicar parte dela.
A implementação desse armazenamento/sincronização real pertence à integração
SCRUM-13; nesta etapa, fake transacional nos testes comprova as operações.
Não criar uma coleção pronta como armazenamento de produção provisório.

O lote contém ID estável, valores anteriores/posteriores e exclusões, inclusive
as duas versões da data: informação suficiente para o responsável atualizar
Lista e índice AVL. Repositório, Lista e AVL não são acessados pelo modelo.
Preparar um lote não altera estado; desistir da confirmação o descarta.
Aplicação rejeita lote obsoleto: o estado anterior deve continuar coincidindo
com o estado atual antes da publicação. A futura integração garante atomicidade
entre memória e JSON; não afirmar que essa integração estará pronta em SCRUM-8.

Consultas retornam objetos imutáveis e filtros com lista explícita de campos,
separando local da ocorrência de guarda. ID, status e vínculo não são campos
editáveis por atualização genérica. IDs repetidos e registros inexistentes
produzem erros explícitos; erros de domínio usam app/erros.py.

Os protocolos externos existentes com ator permanecem como fronteira de
SCRUM-16. O núcleo não autentica nem autoriza usuários e não é registrado em
rotas. Só serviços autenticados poderão solicitar confirmação de vínculo e
operações protegidas. ADMINISTRADOR não ganha permissão de secretário.

## Transições propostas

- Criação sempre ABERTO; entrada não pode impor ID/status/vínculo arbitrários.
- Vínculo 1:1 opcional entre tipos opostos, ambos abertos, com confirmação do
  secretário na camada de serviços. Sugestões nunca criam vínculo.
- Vincular não resolve automaticamente. Confirmar devolução resolve ambos
  em um lote; resolução isolada também exige confirmação na camada de serviços.
- Reabrir um par reabre ambos e mantém vínculo; registro isolado também reabre.
- Proposta conservadora: cancelar só registro ABERTO sem vínculo. Cancelamento
  de par é rejeitado até a equipe decidir a propagação; não inventar regra.
- Exclusão física remove a ocorrência e limpa a referência no parceiro,
  preservando dados e status deste. Foto não é apagada pelo núcleo.
- Falha de validação, lote obsoleto ou abandono de confirmação preservam estado.
- Não desfazer/substituir vínculo implicitamente por edição.

## Registros legados e decisões abertas

Sem migração silenciosa de registros sem foto: codec rejeita com erro claro;
política de recuperação/migração fica documentada como pendente para integração.
A rejeição não apaga nem regrava o arquivo original.

Obtenção de ator confiável, envio de imagens, limites de upload, persistência de
contas e dados, locks e publicação atômica de Lista/AVL/JSON não fazem parte
desta implementação. Justificativa de cancelamento, categorias finais e demais
campos obrigatórios continuam sujeitos a revisão; não apresentá-los como
aprovação coletiva em docs/pendencias.md.

## Validação e entrega

Testes unitários reais para foto obrigatória nos dois tipos, identidade,
codec, datas distintas, guarda, CRUD, filtros, edição sem troca de ID,
exclusão com vínculo, pares resolvidos/reabertos, rejeição de dados inválidos,
abandono, conflito de lote e aplicação atômica com fake. Os testes existentes
da base Flask também devem passar com python -m pytest.

Atualizar documentação de contratos e fornecer exemplo de uso interno e comando
de teste. Entregar SCRUM-8 com suas dependências de integração explícitas,
sem afirmar que CRUD web ou sincronização JSON já funcionam. Só depois iniciar
SCRUM-9 mediante continuidade da conversa.
