# Comandos administrativos locais

Responsável: Luís. Integração dos dados de ocorrências: Matheus.

A CLI fica em `app/cli.py` e é habilitada com `PUC_CONTAS_HABILITADAS=true`.
Prepare `.env` e dependências conforme o
[guia de validação](../docs/desenvolvimento-luis.md).

```sh
python -m flask --app app contas inicializar
python -m flask --app app contas preparar-arquivo
python -m flask --app app contas importar-sqlite instance/contas.sqlite3
python -m flask --app app contas recuperar-administrador
```

- `inicializar`: prepara o JSON e cria somente o primeiro administrador,
  pedindo nome, e-mail `@pucpr.edu.br`, senha oculta e confirmação. Repetir
  recusa criar outro administrador ou substituir o existente.
- `preparar-arquivo`: cria um JSON vazio ou valida o existente, sem apagar
  contas e sem criar administrador.
- `importar-sqlite ORIGEM`: converte explicitamente contas do protótipo SQLite
  v1/v2 para um JSON novo. Preserva IDs/hashes, não modifica a origem e recusa
  destino existente. Executar antes do bootstrap quando houver legado a importar.
- `recuperar-administrador`: após confirmação explícita do operador local,
  redefine e-mail/senha da conta inicial existente e invalida seus acessos,
  mantendo ID e nome. Não cria outra conta. Serve também para adaptar um login
  genérico antigo para o e-mail institucional.

O destino vem de `PUC_CONTAS_JSON`. Usar um processo por arquivo e executar
CLI com servidor parado. Fábrica e consultas não criam ou migram persistência. Não há endpoint de criação/recuperação de administradores,
senha padrão ou senha em argumento de terminal. Os comandos de senha usam
entrada oculta e confirmação; nenhum segredo deve entrar no Git.
