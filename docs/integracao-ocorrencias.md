# Fronteira de ocorrências de Luís — 02/11/2026

A parte de Luís entrega rotas, autorização, entrada/saída, fotos e composição
por injeção. O núcleo de operações continua com Marcelo; carga, persistência
JSON e publicação coerente da Lista/AVL continuam com Matheus; a consulta por
período continua com Leandro. Não há implementação desses módulos em substituição
aos colegas. Os fakes de `tests/` não são usados na configuração padrão.

## O que está concluído

- Cadastro e consulta públicos, filtros combinados, busca textual/código e período.
- Projeções explícitas: objeto, tipo/status, categoria, data/local, descrição,
  cor, foto e guarda pública. Sem hashes, contas, referências de arquivos,
  nós, estruturas, recebimento, destinação ou vínculo interno.
- Edição, exclusão, vínculo e status exigem secretário ativo tanto na rota
  quanto no serviço. Administrador não herda esses poderes.
- Devolução exige confirmação presencial explícita. Resolução/reabertura e
  exclusão de pares delegam o lote inteiro ao núcleo.
- Cancelamento segue a escolha de Luís: ABERTO sem vínculo, sem justificativa
  por enquanto. O núcleo continua rejeitando cancelamento de par.
- Foto obrigatória nos dois tipos, JPEG/PNG até 1.500.000 bytes. Pillow verifica
  o arquivo e decodifica seus bytes; nomes de upload são ignorados e o servidor
  gera uma referência aleatória. Diretório fora de `static/`.
- Foto é servida por ID da ocorrência, sem URL de arquivo interno. Foto nova é
  descartada se preparação/confirmação falhar. Fotos antigas são mantidas até
  definir o descarte de P04; excluir a ocorrência deixa sua URL de foto inacessível.
- Formulários Jinja com CSRF, sucesso em POST → redirect 303, mensagens e
  preservação de campos seguros em erro. Templates mínimos para Mariana revisar.

## Contrato de composição

Por padrão, `OCORRENCIAS_HABILITADAS=False`; nenhuma rota desse módulo é
registrada e nenhum dado é criado. Para habilitar, contas também precisam
estar habilitadas. A fábrica cria `FotosLocais` (`app/repositories/fotos.py`) e `AtendimentoOcorrencias` e
registra as rotas somente após receber dependências concretas válidas.

`app/composicao.py` define:

```python
@dataclass(frozen=True)
class DependenciasOcorrencias:
    nucleo: NucleoOcorrenciasPorta
    consulta_periodo: ConsultaPeriodoPorta
```

`OCORRENCIAS_COMPOSITOR` recebe uma função `compor(config)` ou o texto
`"modulo_real:funcao"`. Ela deve carregar e validar o JSON de ocorrências,
preparar a Lista e a AVL manuais, montar o armazenamento que aplica lotes
indivisíveis, criar o núcleo de Marcelo e a consulta de Leandro e devolver
`DependenciasOcorrencias`. Falha de carga deve abortar a inicialização, sem
publicar estado parcial ou substituir arquivo inválido por vazio.

**Esse compositor de produção ainda depende da entrega dos responsáveis.**
A fábrica, os contratos de entrada e o serviço de Luís estão prontos para
recebê-lo. Não ligar o núcleo diretamente a rotas nem apontar a configuração
para os fakes dos testes. Sem compositor concreto, habilitar o módulo produz
erro explícito de inicialização; não ativa um CRUD fictício.

Depois da integração dos componentes, configurar localmente:

```dotenv
PUC_CONTAS_HABILITADAS=true
PUC_OCORRENCIAS_HABILITADAS=true
PUC_OCORRENCIAS_COMPOSITOR=modulo_real:funcao
PUC_FOTOS_DIRETORIO=instance/fotos
```

`modulo_real:funcao` é um marcador de documentação, não um módulo existente.
A função é chamada uma vez por app. Instâncias não compartilham serviços globais.
A consulta temporal é delegada a `buscar_periodo(inicio, fim)`; o HTTP não
substitui a AVL por varredura. Cada responsável deve garantir o uso das
estruturas acadêmicas no armazenamento/consulta de produção.

## Entrada do serviço

`AtendimentoOcorrencias(nucleo, consulta_periodo, contas, fotos, *,
setor_publico=True, cancelamento_habilitado=True)` é composto pela fábrica com
as escolhas da configuração. Portas completas consumidas em
`app/services/atendimento_ocorrencias.py`; o núcleo segue os métodos publicados
`obter`, `listar`, `preparar_*` e `confirmar(lote)` de Marcelo.

A porta externa `ServicoOcorrenciasPorta` foi atualizada junto aos consumidores:

```python
cadastrar(dados, *, foto: BinaryIO | None) -> OcorrenciaPorta
editar(id, dados, *, ator, foto: BinaryIO | None = None) -> OcorrenciaPorta
excluir(id, *, ator, confirmacao: bool = False) -> None
alterar_status(id, novo_status, *, ator, contexto) -> Iterable[OcorrenciaPorta]
vincular(perdido_id, encontrado_id, *, ator) -> Iterable[OcorrenciaPorta]
```

Cadastro aceita tipo, nome, categoria, data da ocorrência, local, descrição,
cor e dados de guarda. Foto é recebida em separado, nunca como caminho do
navegador. ID, status, referência de foto e vínculo são gerados/controlados pelo
backend. Recebimento e destinação são internos e não entram no cadastro público.

Edição não aceita tipo, ID, status ou vínculo. Recebimento e destinação podem
ser corrigidos pelo secretário, sujeitos às validações do modelo. Datas de
formulário são convertidas para `date`; campos desconhecidos são rejeitados.
O núcleo continua responsável pela validação dos objetos, guarda e transições.

Atores são recarregados pelo ID no JSON de contas, conferindo atividade,
perfil e versão de sessão. Não se confia em perfil/ator enviados pelo navegador.
`contexto` de status aceita somente `confirmacao_presencial: bool`; resolver
exige `True`. Vínculo não confirma devolução nem altera status automaticamente.

## HTTP

| Caminho | Método | Campos principais / controle |
| --- | --- | --- |
| `/ocorrencias` | GET | `q`, tipo, status, categoria, local, guarda, início/fim |
| `/ocorrencias/nova` | GET/POST | Tipo + campos de objeto/guarda + foto obrigatória |
| `/ocorrencias/<id>` | GET | Detalhe público; controles extras somente ao secretário |
| `/ocorrencias/<id>/foto` | GET | Bytes JPEG/PNG do registro existente, sem caminho do cliente |
| `/ocorrencias/<id>/editar` | GET/POST | Secretário; campos de objeto/guarda e foto nova opcional |
| `/ocorrencias/<id>/excluir` | POST | Secretário + `confirmacao=sim` |
| `/ocorrencias/<id>/status` | POST | Secretário + `novo_status`; resolver exige `confirmacao_presencial=sim` |
| `/ocorrencias/vinculos` | POST | Secretário + `perdido_id`, `encontrado_id` |

Quando o módulo está habilitado, `GET /openapi.json` e `GET /swagger` passam a
incluir automaticamente essas rotas, seus parâmetros de filtro e esquemas de
formulário/multipart, refletindo também `SETOR_GUARDA_PUBLICO`,
`CANCELAMENTO_HABILITADO` e `FOTOS_LIMITE_BYTES`.

Nomes de filtro: `q`, `tipo`, `status`, `categoria`, `local_ocorrencia`,
`situacao_guarda`, `setor_guarda`, `inicio`, `fim`. Tipo/status/guarda são
vocabulários fechados; os outros filtros são exatos, combinados por E. `q`
procura trecho em ID/nome/descrição, ignorando maiúsculas/minúsculas. Período
exige as duas datas, início ≤ fim, e preserva a ordem da consulta injetada.
Sem paginação nesta versão local de avaliação.

Todos os POSTs exigem CSRF do mesmo cookie. Arquivo é campo `foto` do multipart;
campos/arquivos duplicados ou extras são recusados. O corpo total comporta o
limite da foto + 64 KiB para campos/cabeçalhos. GET nunca modifica dados.

Erros HTML: 400 validação, 403 permissão/CSRF, 404 registro ausente, 409 conflito
na confirmação de lote, 413 corpo excessivo, 415 conteúdo sem formulário,
503 persistência indisponível (sem caminhos internos). Sem login, ações
protegidas redirecionam para `/login`. `Cache-Control: no-store` nas respostas.

## Validação e limites reais

Executar `python -m pytest`. Os testes desta branch usam contas JSON reais,
fotos reais em `tmp_path` e portas fake de ocorrências exclusivamente em testes.
Um ensaio isolado também executou os fluxos contra o núcleo publicado de
Marcelo e a AVL de Leandro, com armazenamento adaptado somente para o ensaio.
Isso não equivale à carga/persistência de produção completa de SCRUM-13.

Pillow foi acrescentado somente para validar arquivos de imagem; não implementa
Lista, AVL ou correspondência. Referências: [verificação de imagem](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify)
e [upload de formulários Flask](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/).

A ferramenta de navegador não estava disponível para a conferência visual.
Os fluxos de formulário e o HTML foram testados pelo cliente Flask. Mariana
segue com o acabamento visual e Luís com sua validação manual. A conclusão
da aplicação de produção depende das entregas dos colegas; a fronteira HTTP,
autorização, uploads e ponto de composição de Luís estão implementados.
