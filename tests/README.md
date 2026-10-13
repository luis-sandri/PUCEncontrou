# Organização dos testes

- `test_app.py`: testes executáveis da base Flask mantidos por Luís.
- `unit/`: testes de cada módulo, pelo responsável pelo módulo.
- `integration/`: testes entre módulos, coordenados por André.
- `conftest.py`: fixtures comuns; coordenar mudanças com Luís e André.

Executar `python -m pytest` na raiz. Os testes existentes verificam somente
a base. Não há testes pulados que deem a impressão de módulos concluídos.

Se o ambiente de execução restringir a pasta temporária do sistema, usar
`python -m pytest --basetemp .tools/pytest-temporarios`. Esse diretório é
exclusivo do pytest, pode ser limpo por ele e está ignorado pelo Git; não
apontar `--basetemp` para uma pasta com arquivos que devam ser preservados.

Para desenvolver em paralelo, cada integrante pode criar fakes locais dos
protocolos usados pelo seu módulo. Não implementar um armazenamento global
com estruturas prontas para substituir a Lista ou a AVL de produção.

Próximos testes, depois de revisar os contratos: redimensionamento e índices
da Lista; rotações LL/RR/LR/RL, duplicatas e remoção na AVL; reconstrução a
partir do JSON; falha de escrita sem estado parcial; autenticação e matriz
de permissões; resolução e reabertura de pares; correspondência sem efeitos
colaterais. Os cenários dependentes de propostas esperam a aprovação.

Usar `tmp_path` para JSON/SQLite, registros fictícios identificados como
fixtures e senhas de teste sem uso real. Nunca carregar `instance/` local.
