# PUC Encontrou

Base de um sistema web de achados e perdidos da PUCPR, desenvolvido por seis
integrantes para uma disciplina de Engenharia de Software.

**Etapa atual:** aplicação Flask mínima e núcleo da SCRUM-8 implementados.
O modelo imutável, codec e operações de CRUD/vínculos estão testados por lotes
com armazenamento fake. Somente `GET /` e arquivos estáticos estão disponíveis
na web. Lista, AVL, persistência e serviços de autorização/upload ainda precisam
ser integrados. Consulte o [guia da SCRUM-8](docs/scrum-8.md).

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
JSON, SQLite, administrador ou diretórios de persistência nesta etapa.

O depurador é para uso local. O frontend inicial usa Bootstrap 5.3.8 via
CDN com integridade; o carregamento desses estilos requer internet.
Jinja2 e Werkzeug vêm com Flask.
Não há Node, ferramenta de build ou biblioteca de IA como dependência.

## Testar

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Os testes verificam a base Flask, modelo, codec, CRUD interno, integridade dos
pares, conflitos e lotes. A infraestrutura de produção ainda não é exercitada:
o armazenamento fake dos testes não substitui a Lista manual nem a persistência.
Os testes dos módulos ficam em `tests/unit/` e `tests/integration/`.
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
  repositories/          JSON de ocorrências (Matheus), contas (Luís; migração pendente)
  routes/                HTTP e autorização (Luís)
  templates/             Jinja2 (Mariana)
  static/                CSS, JavaScript e imagens (Mariana)
tests/                   unidade por módulo; integração com André
docs/                    decisões, contratos, pendências e análise
scripts/                 espaço para inicialização segura futura
.vscode/                 configuração compartilhável
instance/                dados locais futuros, ignorados pelo Git
```

As classes terminadas em `Porta` são `typing.Protocol`: descrevem
assinaturas para consumidores e fakes, não executam funcionalidades e não
devem ser instanciadas. Não representam a implementação acadêmica de Lista
ou AVL. Não há composição dos serviços de negócio na fábrica ainda.

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
em memória; a AVL manual é um índice auxiliar de datas e IDs. Contas também
serão persistidas em JSON por decisão informada em 19/10/2026. O esboço legado
`sqlite_contas.py` e `CONTAS_SQLITE` ainda aguardam adequação pelo responsável;
não são uma implementação ativa de persistência. Interface e rotas não acessam
dados diretamente. Foto é obrigatória nos dois tipos de ocorrência.

Categorias e campos exatos continuam em revisão. Para a equipe avaliar,
foram selecionadas as seguintes propostas: data de perda/achado para a AVL;
pontuação inicial de correspondência **somente para testes**; exclusão
física; vínculo 1:1 criado por secretário; justificativa obrigatória
para cancelar; gestão de contas de secretário com cadastro, edição,
desativação e redefinição de senha. **Nenhuma dessas seleções é ainda
aprovação coletiva**, e os efeitos e contratos pendentes constam em
[pendências](docs/pendencias.md). A SCRUM-8 usa o desenho aprovado por Marcelo
em 27/10/2026, incluindo exclusão física e regras provisórias de campos e
transições descritas no guia; isso não registra aprovação coletiva fictícia.
Não há entrevistas ou dados reais incluídos nesta base.
Contas, hashes, arquivos locais e segredos não devem entrar no Git. Nenhuma
alteração de Jira, publicação, commit ou push faz parte desta preparação.

## Referências técnicas

- [Fábricas de aplicação Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [Configuração e SECRET_KEY no Flask](https://flask.palletsprojects.com/en/stable/config/)
- [Organização de testes pytest](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Inclusão de Bootstrap 5 e integridade dos arquivos](https://getbootstrap.com/docs/5.3/getting-started/introduction/)

As referências orientam a implementação técnica; não aprovam regras do projeto.
