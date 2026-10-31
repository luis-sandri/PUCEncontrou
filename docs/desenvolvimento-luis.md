# Módulo de contas de Luís: validação local

Branch: `feat/luis-contas-autenticacao`. Em 30/10/2026, Luís definiu P09 e o
escopo simplificado de P10 nesta conversa e autorizou aplicar ao código.
O domínio **`@pucpr.edu.br`** foi confirmado expressamente. O registro em
[pendências](pendencias.md) distingue essas definições da revisão coletiva.

O foco acadêmico continua sendo a Lista Dinâmica baseada em array e a AVL
manuais. Contas e autenticação dão suporte à aplicação com Flask/Jinja e SQLite.

## O que está disponível

- Login por e-mail institucional; nome e e-mail único nas contas.
- Administrador lista/cadastra/edita/desativa/reativa/redefine senhas de secretários.
- Sessão nativa do Flask, duração absoluta de 30 minutos e consulta da conta no
  backend. Contador na conta invalida acessos após mudança de credenciais/situação.
- Formulários com CSRF, validação e mensagens; POST bem-sucedido redireciona.
- Senhas com hash Werkzeug, SQL parametrizado e dados locais fora do Git.
- CLI para criar o primeiro administrador, atualizar banco e recuperar o acesso local.

A fábrica não acessa persistência. O módulo continua habilitado explicitamente;
não compõe ocorrências, Lista, AVL, JSON ou correspondência. Templates mínimos
permitem testar os fluxos; o acabamento visual segue com Mariana. `base.html` e
os arquivos estáticos existentes foram preservados.

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

A CLI solicita nome, e-mail `@pucpr.edu.br`, senha oculta e confirmação. Não recebe senha
por argumento. Repetir a inicialização recusa criar outro administrador e preserva
o existente. Nenhuma senha padrão é fornecida. Antes do bootstrap, operações que
precisam do banco respondem 503, sem criar arquivo durante requisições.

No Windows, use `.\.venv\Scripts\python.exe` nos comandos conforme o README.

## Atualizar um banco da versão anterior

A nova versão usa esquema SQLite **v2**, sem tabela de sessões. Se já criou um
banco no primeiro protótipo (v1), execute explicitamente, com a aplicação parada:

```sh
.venv/bin/python -m flask --app app contas atualizar-banco
```

O comando preserva contas, IDs e hashes, adiciona o contador de sessão e remove
somente os registros/tabela de sessões antigos. A fábrica e as requisições não
fazem migrações. Cookies antigos deixam de autenticar e será necessário entrar
novamente. Banco desconhecido não é sobrescrito.

A migração preserva identificadores antigos. Se seu administrador foi criado
com login genérico, adapte o acesso para o e-mail institucional pela CLI:

```sh
.venv/bin/python -m flask --app app contas recuperar-administrador
```

Esse comando pede confirmação, e-mail e nova senha oculta/confirmada. Mantém o
mesmo administrador, não cria outro e invalida seus acessos anteriores. É uma
operação local do responsável pelo banco; não existe recuperação pública.
Secretários com login antigo podem ter o e-mail corrigido pela tela administrativa.

## Testar no navegador

1. Abra `http://127.0.0.1:5000/login` e entre com o administrador criado na CLI.
2. Em **Secretários**, cadastre nome, e-mail `@pucpr.edu.br`, senha e confirmação.
3. Em **Gerenciar**, altere nome/e-mail, redefina senha ou desative/reative a conta.
4. Entre com o secretário em outro navegador ou janela privada. Ele acessa sua
   sessão, mas não gerencia contas. Desativar ou redefinir a senha pelo administrador
   exige que o secretário faça novo login.
5. Use **Sair** para limpar o acesso do navegador atual.

As telas funcionam com formulários, sem cliente JSON ou JavaScript de autenticação.
Sucesso redireciona com mensagem. Erros preservam nome/e-mail, sem preencher senha.
A listagem vazia e os erros também têm telas. Não há rota de criação pública
nem tela para novos administradores.

Nome tem 1–120 caracteres sem controles; e-mail institucional tem até 120,
normalizado com `strip`/`casefold`; senha tem 12–128 caracteres Unicode válidos,
sem normalização. Os limites são técnicos para revisão da equipe.

O [contrato HTTP](contratos.md) descreve caminhos, campos e códigos de resposta.

## Validar automaticamente

```sh
.venv/bin/python -m pytest
```

Os testes usam somente `tmp_path`, contas fictícias e cliente Flask. Verificam
CLI, migração v1→v2 preservando contas, recuperação local, persistência após
reabertura, formulários, campos extras, CSRF, autorização, domínio de e-mail,
expiração, reset/desativação/reativação e rollback de dados + contador em falha.

## Limites desta entrega

P09 e a parte de contas de P10 estão definidos por Luís para esta branch;
revisão coletiva e acabamento com Mariana continuam pendentes. Os fluxos de
ocorrências dependem das decisões e implementações dos responsáveis.

Logout limpa o cookie atual; sem registro de sessões no banco, não revoga uma
cópia roubada do cookie. Reset e mudança de situação/identificador invalidam
acessos anteriores pelo contador, inclusive após reativação. O escopo é local
acadêmico; limitação de tentativas, recuperação por e-mail e infraestrutura de
publicação ficam fora desta entrega. Se houver publicação, revisar HTTPS/cookie
Secure. Usar `--debug` somente no desenvolvimento local.
