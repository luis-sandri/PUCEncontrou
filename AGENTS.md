# Instruções permanentes

- Leia `README.md` e `docs/` antes de alterar contratos ou regras. O objetivo inicial é uma base executável, sem concluir os módulos dos colegas.
- Preserve as camadas: interface -> rotas Flask -> serviços -> modelos, estruturas e repositórios. Não exponha estruturas, nós, arquivos ou hashes ao frontend.
- Regras aprovadas estão em `docs/regras-negocio.md`; propostas e dúvidas estão em `docs/pendencias.md`. Não transforme propostas em requisitos nem invente entrevistas.
- Os protocolos são esboços técnicos para revisão pelos responsáveis. Mudanças de assinatura devem atualizar `docs/contratos.md`, consumidores e testes na mesma PR.
- Lista Dinâmica com array e AVL devem ser implementadas manualmente pelos responsáveis. Protocolos, mocks e estruturas prontas não cumprem o requisito acadêmico.
- Respeite as responsabilidades em `docs/arquitetura.md`. Não implemente módulos completos de outro integrante sem pedido explícito.
- Correspondência usa regras determinísticas, sem IA; somente sugere candidatos e nunca altera status.
- Autenticação e autorização pertencem ao backend. Não presuma que ADMINISTRADOR herda poderes de SECRETARIO. Senhas somente com hash; segredos e dados locais fora do Git.
- Mantenha a aplicação mínima inicializável sem instanciar contratos. Não registre rotas de negócio até seus serviços estarem implementados e protegidos.
- Use `python -m pytest`; testes futuros de dados usam `tmp_path`. Informe o que foi validado e qualquer limitação real.
- Prefira PRs pequenas por módulo; coordene arquivos compartilhados com Luís. Não altere tarefas do Jira nem envie mensagens externas sem autorização.
