# Comandos administrativos locais

Responsável: Luís. Integração dos dados de ocorrências: Matheus.

A CLI fica em `app/cli.py` e é habilitada com `PUC_CONTAS_HABILITADAS=true`.
Prepare `.env` e dependências conforme o
[guia de validação](../docs/desenvolvimento-luis.md).

```sh
python -m flask --app app contas inicializar
python -m flask --app app contas atualizar-banco
python -m flask --app app contas recuperar-administrador
```

- `inicializar`: prepara o esquema e cria somente o primeiro administrador,
  pedindo nome, e-mail `@pucpr.edu.br`, senha oculta e confirmação. Repetir
  recusa criar outro administrador ou substituir o existente.
- `atualizar-banco`: cria o esquema vazio ou migra v1→v2, preservando contas e
  hashes, adicionando o contador de sessão e removendo a tabela de sessões do
  protótipo. Execute com a aplicação parada; será necessário novo login.
- `recuperar-administrador`: após confirmação explícita do operador local,
  redefine e-mail/senha da conta inicial existente e invalida seus acessos,
  mantendo ID e nome. Não cria outra conta. Serve também para adaptar um login
  genérico antigo para o e-mail institucional.

O caminho vem de `PUC_CONTAS_SQLITE`. Fábrica e consultas não criam ou migram
persistência. Não há endpoint de criação/recuperação de administradores,
senha padrão ou senha em argumento de terminal. Os comandos de senha usam
entrada oculta e confirmação; nenhum segredo deve entrar no Git.
