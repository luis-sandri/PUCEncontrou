# Backend de Luís para validação

Branch: `feat/luis-contas-autenticacao`. Implementação candidata de P09/P10,
sem registrar aprovação coletiva nem alterar as regras de negócio aprovadas.
As escolhas abaixo são técnicas e provisórias para permitir a revisão local.

## Escopo entregue

- Modelos imutáveis de conta e projeções explícitas sem hash.
- SQLite com esquema versionado, parâmetros SQL, transações e IDs UUID.
- Administrador inicial único, provisionado somente por CLI interativa.
- Autenticação com hashes Werkzeug e respostas de falha genéricas.
- Sessões opacas com expiração absoluta de 30 minutos; SQLite armazena somente
  o SHA-256 do token de sessão. O cookie assinado contém token e CSRF, sem perfil
  ou credenciais. A conta ativa é consultada no backend em cada requisição.
- Somente administrador ativo pode listar/cadastrar/editar/desativar/redefinir
  senha de secretários. A alteração não pode atingir uma conta administrativa.
- Desativação, troca de identificador ou redefinição de senha revogam todas as
  sessões da conta na mesma transação. Logout revoga a sessão no servidor.
- Rotas JSON com CSRF, lista explícita de campos e limite de corpo de 16 KiB.

A fábrica não acessa persistência, inclusive quando o módulo é habilitado.
Ocorrências, Lista, AVL, JSON e correspondência não são compostos nem expostos.
As telas Jinja continuam com Mariana; estas rotas permitem testar o backend.

## Executar neste Mac

Na raiz do repositório, com Python instalado (3.12 continua recomendado):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

O ambiente `.venv` já foi preparado neste PC. Os testes desta alteração foram
executados com Python 3.15.2; compatibilidade com 3.12 deve ser verificada no
ambiente padronizado da equipe antes da entrega.

Somente se ainda não houver `.env`, crie uma configuração local sem exibir a chave:

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import secrets

conteudo = Path('.env.example').read_text(encoding='utf-8')
conteudo = conteudo.replace('PUC_SECRET_KEY=', 'PUC_SECRET_KEY=' + secrets.token_hex(32), 1)
with Path('.env').open('x', encoding='utf-8') as arquivo:
    arquivo.write(conteudo)
PY
```

O modo `x` recusa sobrescrever uma configuração existente. Para experimentar o
módulo, altere **no `.env` local** `PUC_CONTAS_HABILITADAS=false` para `true`.
Mantenha `PUC_SESSION_COOKIE_SECURE=false` somente no desenvolvimento HTTP local;
HTTPS exige `true`. Não coloque `.env`, SQLite ou credenciais no Git.

```sh
.venv/bin/python -m flask --app app contas inicializar
.venv/bin/python -m flask --app app run --debug
```

A CLI solicita nome, identificador, senha oculta e confirmação. Não recebe senha
por argumento. Repetir a inicialização recusa criar outro administrador e preserva
o existente. Nenhuma senha padrão é fornecida. Antes do bootstrap, operações que
precisam do banco respondem 503, sem criar arquivo durante requisições.

No Windows, use `.\.venv\Scripts\python.exe` nos comandos conforme o README.

## Contrato para experimentar com cliente HTTP

Use um cliente que preserve cookies. Obtenha o CSRF com `GET /login` e envie seu
valor no cabeçalho `X-CSRF-Token` ao fazer `POST /login` com JSON contendo
`identificador` e `senha`. Use o **novo** `csrf_token` retornado após o login em
todas as mutações seguintes. O token anterior deixa de valer no cookie atual.

| Operação | Método e caminho | JSON de entrada | Resultado |
| --- | --- | --- | --- |
| Preparar login | `GET /login` | — | `{csrf_token}` |
| Autenticar | `POST /login` | `identificador`, `senha` | `{conta, csrf_token}` |
| Sessão atual | `GET /sessao` | — | `{conta, csrf_token}` |
| Encerrar sessão | `POST /logout` | — | 204 |
| Listar secretários | `GET /contas/secretarios` | — | `{contas: [...]}` |
| Cadastrar secretário | `POST /contas/secretarios` | `nome`, `identificador`, `senha` | 201, `{conta}` |
| Alterar secretário | `PATCH /contas/secretarios/<id>` | Um ou mais: `nome`, `identificador`, `ativa: false`, `senha` | `{conta}` |

Somente os cinco campos `id`, `perfil`, `nome`, `identificador` e `ativa` compõem
`conta`. Não aceitar `perfil`, `ator` ou `senha_hash` enviados pelo cliente.
O identificador é genérico (não exige e-mail), tem 3–120 caracteres, é normalizado
com `strip`/`casefold` e não aceita espaços ou controles. Nome tem 1–120 caracteres
após `strip`, sem controles. Senha tem 12–128 caracteres Unicode codificáveis em
UTF-8 e não é normalizada.
Estes limites aguardam revisão da equipe, assim como o HTTP JSON e o tempo da sessão.

Erros têm a forma `{erro: mensagem}`: 400 para entrada inválida, 401 para sessão
ausente/inválida ou falha de login, 403 para permissão/CSRF, 404 para secretário
inexistente, 409 para identificador em uso, 413 para corpo excessivo, 415 para
conteúdo sem JSON e 503 para persistência indisponível. Falhas de login não dizem
se o identificador existe. Respostas do módulo usam `Cache-Control: no-store`.

## Validar

```sh
.venv/bin/python -m pytest
```

Os testes usam somente SQLite em `tmp_path` e contas fictícias. Incluem fluxo
CLI → SQLite → serviços → HTTP, matriz de acesso, campos extras, CSRF de outro
cliente/rotacionado, expiração, replay de cookie depois de logout, reset e
desativação, concorrência entre reset e login e rollback de alteração + revogação.

## Limitações para revisão

P09/P10 continuam pendentes. Não há reativação, exclusão de contas, novos
administradores, recuperação pública, alteração de credenciais próprias ou
permissão administrativa sobre ocorrências. A integração dessas rotas com as
telas depende do alinhamento com Mariana. Não há dados reais ou validação coletiva.

Esta versão se destina à avaliação local. Limitação de tentativas de login,
limpeza periódica de sessões expiradas, recuperação de acesso e configuração
de implantação HTTPS ainda precisam ser definidas antes de exposição pública.
O comando Flask com `--debug` deve ser usado somente localmente.
