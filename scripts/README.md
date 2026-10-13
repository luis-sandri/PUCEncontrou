# Scripts administrativos futuros

Responsável: Luís; integração de dados: Matheus.

Nenhum script de criação de contas é fornecido nesta etapa. A conta inicial
de ADMINISTRADOR deverá ser criada por uma CLI local segura, antes do uso
administrativo, sem endpoint público de cadastro de administradores.

Contrato de segurança para a implementação futura: solicitar senha com
entrada oculta (`getpass`), confirmar a entrada, aplicar hash de senha,
usar transação SQLite e impedir criação repetida silenciosa. Não passar
senhas em argumentos de terminal, gravá-las em fixtures ou definir conta
padrão. A política para recuperar o acesso inicial deve ser revisada pela equipe.

Scripts futuros devem receber caminhos externos, respeitar a configuração
do projeto e nunca sobrescrever dados existentes sem tratamento explícito.
