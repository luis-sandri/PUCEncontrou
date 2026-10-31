# Organização dos testes

- `test_app.py`: testes executáveis da base Flask mantidos por Luís.
- `unit/`: testes de cada módulo, pelo responsável pelo módulo.
- `integration/`: testes entre módulos, coordenados por André.
- `conftest.py`: fixtures comuns; coordenar mudanças com Luís e André.

Executar `python -m pytest` na raiz. Além da base, a branch de Luís testa o
módulo de contas de Luís: `unit/test_sqlite_contas.py`,
`unit/test_servicos_contas.py`, `integration/test_contas_cli.py` e
`integration/test_contas_http.py`. A integração usa CLI, SQLite temporário e
cliente Flask reais, com formulários HTML, domínio institucional, autorização,
CSRF, sessão Flask, reativação, recuperação local, migração v1→v2 e falhas
transacionais. Todos os dados persistidos usam `tmp_path`. Não há testes pulados que deem a impressão de módulos concluídos.

Se o ambiente de execução restringir a pasta temporária do sistema, usar
`python -m pytest --basetemp .tools/pytest-temporarios`. Esse diretório é
exclusivo do pytest, pode ser limpo por ele e está ignorado pelo Git; não
apontar `--basetemp` para uma pasta com arquivos que devam ser preservados.

Para desenvolver em paralelo, cada integrante pode criar fakes locais dos
protocolos usados pelo seu módulo. Não implementar um armazenamento global
com estruturas prontas para substituir a Lista ou a AVL de produção.

Próximos testes, depois de revisar os contratos: redimensionamento e índices
da Lista; rotações LL/RR/LR/RL, duplicatas e remoção na AVL; reconstrução a
partir do JSON; falha de escrita sem estado parcial em ocorrências;
resolução e reabertura de pares; correspondência sem efeitos
colaterais. Os cenários dependentes de propostas esperam a aprovação.

Usar `tmp_path` para JSON/SQLite, registros fictícios identificados como
fixtures e senhas de teste sem uso real. Nunca carregar `instance/` local.
