# PUC Encontrou

## Integração SCRUM-9 — 06/11/2026

A classe `ListaDinamica[T]` está implementada em `app/structures/lista_dinamica.py`,
com buffer fixo, expansão por duplicação, cópia e deslocamento manuais, busca
e filtragem por predicados. Veja [o guia SCRUM-9](docs/scrum-9.md).
O modelo e o núcleo SCRUM-8, a AVL e os módulos de contas, autorização e fotos
da main foram preservados. A composição de produção conecta o JSON, a Lista,
a AVL, o núcleo e a consulta temporal.
A representação do buffer deve ser conferida com a rubrica acadêmica (P11).
As seções datadas anteriores preservam o histórico das entregas.

## Integração SCRUM-8 com a main

O modelo imutável, codec e núcleo CRUD de Marcelo estão implementados em
`app/models/ocorrencia.py`, `app/models/alteracao_ocorrencias.py` e
`app/services/nucleo_ocorrencias.py`. Consulte [o guia SCRUM-8](docs/scrum-8.md).
As implementações de contas JSON, autorização, upload e rotas de Luís e a AVL
de Leandro foram preservadas. O núcleo usa lotes com estados anteriores e
posteriores; a composição real com Lista/AVL/JSON ainda depende da integração.
Foto é obrigatória nos dois tipos. A exclusão é física e limpa o vínculo no
parceiro sem excluí-lo. Cancelamento de par permanece bloqueado conforme o
desenho aprovado da SCRUM-8. Categorias e campos finais continuam em revisão.
As referências abaixo a núcleo/modelo ainda não implementados são históricas.

Base de um sistema web de achados e perdidos da PUCPR, desenvolvido por seis
integrantes para uma disciplina de Engenharia de Software.

**Etapa atual:** base Flask, contas, fronteira HTTP, núcleo SCRUM-8, Lista manual SCRUM-9, AVL e composição de produção implementados.
Por padrão, somente `GET /`, a documentação HTTP ativa (`/swagger` e `/openapi.json`) e arquivos estáticos estão disponíveis.
Esta branch acrescenta o módulo de contas em JSON e a fronteira HTTP de
ocorrências. A composição local de ocorrências usa o núcleo, a Lista Dinâmica,
a AVL manual e o repositório JSON. Consulte o [guia de validação de contas](docs/desenvolvimento-luis.md)
e o [contrato de integração](docs/integracao-ocorrencias.md).

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
$env:PUC_OCORRENCIAS_HABILITADAS = "false"
.\.venv\Scripts\python.exe -m flask --app app ocorrencias inicializar
Remove-Item Env:\PUC_OCORRENCIAS_HABILITADAS
.\.venv\Scripts\python.exe -m flask --app app contas inicializar
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Faça a cópia e a geração da chave **somente na primeira configuração**.
Não sobrescreva um `.env` existente. A geração grava a chave no arquivo
local ignorado pelo Git e não a exibe no terminal. Se `py` não estiver
disponível, use o executável de Python instalado no seu computador para
criar o ambiente. Um `.venv` já preparado dispensa a criação novamente.
Os dois comandos `inicializar` também são de uso único. O de contas solicita
nome, e-mail institucional e senha do administrador no terminal; execute-o
com o servidor parado. Se já houver dados, não repita esses comandos.

Abra `http://127.0.0.1:5000/`. O Flask CLI carrega `.env` com python-dotenv;
uma chamada Python direta a `create_app` recebe configuração explícita ou
variáveis de ambiente. A fábrica recusa iniciar sem `SECRET_KEY` e não cria
JSON de contas/ocorrências, administrador ou diretórios de persistência.

Para habilitar as telas públicas de ocorrências, prepare uma vez o snapshot
local antes de ligar `PUC_OCORRENCIAS_HABILITADAS=true` no `.env`:

```powershell
.\.venv\Scripts\python.exe -m flask --app app ocorrencias inicializar
```

O comando cria somente um JSON vazio se ele ainda não existir; se já existir,
valida-o sem sobrescrever. Ative também `PUC_CONTAS_HABILITADAS=true` para
as telas de login/equipe. O primeiro administrador é criado separadamente
com `flask --app app contas inicializar`, que solicita os dados no terminal
sem colocar a senha em argumentos ou no Git. Reinicie o servidor após alterar
o `.env`.

O depurador é para uso local. O frontend inicial usa Bootstrap 5.3.8 via
CDN com integridade, e `/swagger` carrega a interface Swagger UI via CDN sobre `/openapi.json`; o carregamento desses ativos requer internet.
JSON faz parte da biblioteca padrão; Jinja2 e Werkzeug vêm com Flask.
Pillow valida as imagens JPEG/PNG; não implementa estruturas acadêmicas.
Não há Node, ferramenta de build ou biblioteca de IA como dependência.

## Testar

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Os testes verificam a base, o isolamento e a ausência de endpoints de negócio
por padrão, além do módulo optativo de contas: JSON temporário, autorização,
CSRF, sessão Flask, reativação, falhas transacionais e CLI sem senha na saída.
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
ou AVL. A composição de ocorrências exige as dependências concretas do núcleo
e da consulta; os serviços de contas só são compostos com `PUC_CONTAS_HABILITADAS=true`; nem essa
composição cria arquivo ou administrador. A CLI explícita prepara o JSON de contas.
A fronteira de ocorrências só é composta com `PUC_OCORRENCIAS_HABILITADAS=true`,
contas habilitadas e `PUC_OCORRENCIAS_COMPOSITOR` apontando para dependências
concretas; não há compositor de produção fictício neste repositório.

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
suas branches; esta adequação não os incorpora. A fronteira HTTP de Luís foi concluída
em 02/11 e aguarda esses componentes reais para ativação integrada.
Contas, hashes, arquivos locais e segredos não devem entrar no Git. Nenhuma
alteração de Jira, publicação, commit ou push faz parte desta preparação.

Em 30/10/2026, Luís definiu nome, e-mail institucional `@pucpr.edu.br`,
reativação, sessão de 30 minutos e recuperação local para seu módulo de contas.
P10 foi simplificado para formulários Flask/Jinja e sessão nativa do Flask;
a API JSON e a tabela de sessões foram removidas. As decisões estão em
[pendências](docs/pendencias.md), sem registrar aprovação coletiva inexistente.
As telas mínimas permitem testar `/login` e a gestão de secretários; Mariana
continua responsável pelo acabamento visual. Em 02/11, Luís confirmou fotos
JPEG/PNG até 1,5 MB, setor de guarda público e cancelamento isolado sem
justificativa por enquanto. Rotas de ocorrências e testes constam no guia de integração.

## Referências técnicas

- [Fábricas de aplicação Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [Configuração e SECRET_KEY no Flask](https://flask.palletsprojects.com/en/stable/config/)
- [Organização de testes pytest](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Inclusão de Bootstrap 5 e integridade dos arquivos](https://getbootstrap.com/docs/5.3/getting-started/introduction/)

As referências orientam a implementação técnica; não aprovam regras do projeto.
