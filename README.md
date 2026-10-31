# PUC Encontrou

Base de um sistema web de achados e perdidos da PUCPR, desenvolvido por seis
integrantes para uma disciplina de Engenharia de Software.

**Etapa atual:** aplicação Flask mínima executável e contratos preliminares.
Por padrão, somente `GET /` e arquivos estáticos estão disponíveis.
Esta branch acrescenta o **módulo de contas de Luís**: contas em JSON,
autenticação simples, formulários Jinja, gestão de secretários e CLI local,
ativados explicitamente para avaliação das escolhas de P09/P10 definidas por Luís. Consulte o
[guia de validação](docs/desenvolvimento-luis.md). Ocorrências, estruturas
acadêmicas, JSON, consultas e correspondência continuam com seus responsáveis.

## Executar no Windows

Abra **a pasta que contém este README e `.git`** no VS Code. Neste ambiente,
ela é `C:\Users\Luis\Desktop\PUCEncontrou\PUCEncontrou`; a pasta externa
é apenas o diretório que contém o clone.

Base técnica inicial: Python 3.12 recomendado, Python 3.11 ou superior;
validar outras versões antes de padronizar a entrega. No PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "from pathlib import Path; import secrets; p = Path('.env'); p.write_text(p.read_text(encoding='utf-8').replace('PUC_SECRET_KEY=', 'PUC_SECRET_KEY=' + secrets.token_hex(32), 1), encoding='utf-8')"
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Faça a cópia e a geração da chave **somente na primeira configuração**.
Não sobrescreva um `.env` existente. A geração grava a chave no arquivo
local ignorado pelo Git e não a exibe no terminal. Se `py` não estiver
disponível, use o executável de Python instalado no seu computador para
criar o ambiente. Um `.venv` já preparado dispensa a criação novamente.

Abra `http://127.0.0.1:5000/`. O Flask CLI carrega `.env` com python-dotenv;
uma chamada Python direta a `create_app` recebe configuração explícita ou
variáveis de ambiente. A fábrica recusa iniciar sem `SECRET_KEY` e não cria
JSON de contas/ocorrências, administrador ou diretórios de persistência nesta etapa.

O depurador é para uso local. O frontend inicial usa Bootstrap 5.3.8 via
CDN com integridade; o carregamento desses estilos requer internet.
JSON faz parte da biblioteca padrão; Jinja2 e Werkzeug vêm com Flask.
Não há Node, ferramenta de build ou biblioteca de IA como dependência.

## Testar

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Os testes verificam a base, o isolamento e a ausência de endpoints de negócio
por padrão, além do módulo optativo de contas: JSON temporário, autorização,
CSRF, sessão Flask, reativação, migração, falhas transacionais e CLI sem senha na saída.
Consulte [a organização dos testes](tests/README.md).

O VS Code oferece extensões recomendadas, descoberta de pytest e execução
Flask com F5. Selecione o interpretador de `.venv` ao abrir a pasta.

## Organização

```text
app/
  __init__.py             fábrica e composição (Luís)
  config.py              configuração externa (Luís)
  erros.py               vocabulário preliminar de erros
  models/                Ocorrência (Marcelo), contas (Luís)
  structures/            Lista Dinâmica (Marcelo), AVL (Leandro)
  services/              CRUD/regras, consultas, correspondência, contas
  repositories/          JSON de ocorrências (Matheus) e de contas (Luís)
  routes/                HTTP e autorização (Luís)
  templates/             Jinja2 (Mariana)
  static/                CSS, JavaScript e imagens (Mariana)
tests/                   unidade por módulo; integração com André
docs/                    decisões, contratos, pendências e análise
scripts/                 instruções da CLI administrativa
.vscode/                 configuração compartilhável
instance/                dados locais, ignorados pelo Git
```

As classes terminadas em `Porta` são `typing.Protocol`: descrevem
assinaturas para consumidores e fakes, não executam funcionalidades e não
devem ser instanciadas. Não representam a implementação acadêmica de Lista
ou AVL. Não há composição dos serviços de ocorrências na fábrica. Os serviços
concretos de contas só são compostos com `PUC_CONTAS_HABILITADAS=true`; nem essa
composição cria arquivo ou administrador. A CLI explícita prepara o JSON de contas.

## Começar o trabalho em equipe

1. Ler [arquitetura e avaliação do paralelo](docs/arquitetura.md),
   [regras aprovadas](docs/regras-negocio.md), [contratos](docs/contratos.md)
   e [pendências](docs/pendencias.md).
2. Cada responsável revisar seu contrato v0 antes de integrar consumidores.
   Alterações de campos, datas e regras seguem as pendências, sem assumir
   aprovação por estarem documentadas ou presentes em anotações de tipos.
3. Desenvolver em branch por módulo e abrir PR pequena com testes do módulo.
   Usar fakes das dependências enquanto os módulos reais não estiverem prontos.
4. Integrar a trilha JSON -> Lista -> AVL e serviços -> rotas -> templates
   progressivamente. Luís coordena a fábrica; André coordena testes integrados.

O JSON é a persistência das ocorrências; a Lista manual contém os registros
em memória; a AVL manual é um índice auxiliar de datas e IDs. Contas
administrativas usam outro JSON, mantido por Luís. Interface e rotas não acessam dados diretamente.

Em 31/10, a pedido de Luís, os pontos conflitantes foram alinhados às regras
registradas nas branches de Marcelo: foto obrigatória nos dois tipos; nome,
categoria, data e local mínimos; vínculo 1:1 de tipos opostos abertos; exclusão
física que limpa o vínculo e preserva o parceiro; cancelamento somente de ABERTO
isolado. Categorias finais, exposição pública, uploads, justificativa e política
de cancelamento de pares continuam em revisão, conforme
[pendências](docs/pendencias.md). Modelo/núcleo/Lista dos colegas permanecem nas
suas branches; esta adequação não os incorpora nem expõe suas rotas.
Contas, hashes, arquivos locais e segredos não devem entrar no Git. Nenhuma
alteração de Jira, publicação, commit ou push faz parte desta preparação.

Em 30/10/2026, Luís definiu nome, e-mail institucional `@pucpr.edu.br`,
reativação, sessão de 30 minutos e recuperação local para seu módulo de contas.
P10 foi simplificado para formulários Flask/Jinja e sessão nativa do Flask;
a API JSON e a tabela de sessões foram removidas. As decisões estão em
[pendências](docs/pendencias.md), sem registrar aprovação coletiva inexistente.
As telas mínimas permitem testar `/login` e a gestão de secretários; Mariana
continua responsável pelo acabamento visual.

**Se já usou o SQLite do protótipo anterior**, consulte a
[importação explícita para JSON e recuperação de acesso](docs/desenvolvimento-luis.md).
A configuração atual é `PUC_CONTAS_JSON=instance/contas.json`; a antiga
`PUC_CONTAS_SQLITE` deixa de ser usada. Nenhum dado local é convertido automaticamente.

## Referências técnicas

- [Fábricas de aplicação Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [Configuração e SECRET_KEY no Flask](https://flask.palletsprojects.com/en/stable/config/)
- [Organização de testes pytest](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Inclusão de Bootstrap 5 e integridade dos arquivos](https://getbootstrap.com/docs/5.3/getting-started/introduction/)

As referências orientam a implementação técnica; não aprovam regras do projeto.
