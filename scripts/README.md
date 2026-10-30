# Inicialização administrativa

Responsável: Luís; integração de dados: Matheus.

A branch de Luís fornece a CLI experimental em `app/cli.py`, habilitada junto
com `PUC_CONTAS_HABILITADAS=true`. Preparar `.env` e dependências conforme o
[guia de validação](../docs/desenvolvimento-luis.md), depois executar:

```sh
python -m flask --app app contas inicializar
```

O comando cria o esquema SQLite e somente o primeiro administrador, pedindo
nome, identificador, senha oculta e confirmação. Repetir recusa criar outro ou
substituir o existente. A fábrica e consultas não inicializam persistência.
Não há endpoint público de cadastro de administradores.

Contrato de segurança implementado na CLI: solicitar senha com
entrada oculta (`getpass`), confirmar a entrada, aplicar hash de senha,
usar transação SQLite e impedir criação repetida silenciosa. Não passar
senhas em argumentos de terminal, gravá-las em fixtures ou definir conta
padrão. A política para recuperar o acesso inicial deve ser revisada pela equipe.

O caminho vem de `PUC_CONTAS_SQLITE`. Scripts futuros devem receber caminhos externos, respeitar a configuração
do projeto e nunca sobrescrever dados existentes sem tratamento explícito.
