# Regras de negócio

Fonte: contexto fornecido pelo solicitante. Não foram realizadas entrevistas
nem consultadas tasks do Jira. Esta página registra somente decisões
informadas como aprovadas. Propostas estão em [pendências](pendencias.md).

## Acesso e responsabilidades aprovadas

- Usuários comuns cadastram e consultam ocorrências sem login.
- Os perfis autenticados são `SECRETARIO` e `ADMINISTRADOR`.
- Secretários editam, excluem e alteram status de ocorrências de **todos os
  blocos**. Não há restrição ao bloco do secretário. Eles não gerenciam contas.
- Administradores cadastram e gerenciam contas de secretários. A administração
  de contas é sua responsabilidade definida.
- A conta inicial de administrador é criada previamente por inicialização
  segura. Não há cadastro público de administradores.
- Autenticação e autorização são protegidas pelo backend; senhas usam hash
  e configurações sensíveis permanecem fora do Git.

Não foi aprovada uma hierarquia em que administrador herda automaticamente
ações de secretário. Também não foi definida a criação de novos
administradores ou a gestão das próprias credenciais. Registrar essas
dúvidas antes de ampliar permissões.

## Ocorrências, status e devolução

- Os tipos envolvidos são `PERDIDO` e `ENCONTRADO`.
- Os status são `ABERTO`, `RESOLVIDO` e `CANCELADO`.
- Uma ocorrência nova começa em `ABERTO`.
- O secretário confirma presencialmente a recuperação do objeto antes de
  marcar uma ocorrência como `RESOLVIDO`.
- É possível vincular uma ocorrência `PERDIDO` e uma `ENCONTRADO`.
- Após a confirmação de devolução pelo secretário, ambas as ocorrências
  vinculadas passam a `RESOLVIDO`.
- Se uma ocorrência vinculada for reaberta, a outra também será reaberta.
- Local de perda/achado e local de guarda/entrega são informações distintas.
  O modelo e os formulários não devem fundi-los em um único campo.

Não há uma matriz completa de transições aprovada. As regras acima não
definem a propagação de cancelamento, o efeito de exclusão sobre um vínculo,
o responsável pela criação/desvinculação ou os limites de cardinalidade.

## Correspondência

- A correspondência automatizada apenas sugere candidatos.
- Ela não confirma a propriedade e não altera status.
- Não usar IA para encontrar correspondências.
- Pontuação, categorias, limite e tratamento de valores ausentes ainda não
  são requisitos aprovados.

## Matriz de acesso para orientar a integração

| Operação | Usuário comum | SECRETARIO | ADMINISTRADOR |
| --- | --- | --- | --- |
| Cadastro e consulta públicos | Sem login | Acesso público disponível | Acesso público disponível |
| Editar/excluir/alterar status em todos os blocos | Não autorizado | Aprovado, com regras de devolução | Poder de secretário não concedido pelo escopo atual; confirmar ampliação |
| Cadastrar e gerenciar contas de secretários | Não autorizado | Não autorizado | Aprovado |
| Criar/desfazer vínculos | Ator não definido | Ator não definido | Ator não definido |
| Criar conta inicial de administrador | Sem endpoint público | Sem endpoint público | Inicialização segura prévia |

O backend deve negar operações não autorizadas. A última linha descreve
um processo local futuro, não um endpoint ou uma permissão de usuário.
