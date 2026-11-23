# Infraestrutura local do Odoo

Este diretório gerencia o ciclo de vida local do Voigt ERP com Docker Compose. Ele é isolado do código da aplicação Odoo e pode ser operado de forma independente, enquanto o serviço Odoo é compilado a partir do `Dockerfile` na raiz do repositório. Não mantemos aqui um segundo Dockerfile da aplicação nem uma cópia do código-fonte do Odoo.

## Pré-requisitos

- Docker Engine ou Docker Desktop com Docker Compose v2 (`docker compose`)
- Git (opcional; usado para registrar na imagem a revisão do código-fonte em uso)
- Portas 8069 e 15432 do computador disponíveis (ou os valores definidos em `ODOO_PORT` e `DB_IDE_PORT`)

## Primeira execução

A partir da raiz do repositório:

```bash
./local-infra/scripts/setup.sh
```

O script de configuração cria `local-infra/.env` com permissão 0600. Edite esse arquivo e substitua `POSTGRES_PASSWORD` e `ODOO_ADMIN_PASSWD` por valores fortes e diferentes, destinados somente ao ambiente local. Essas credenciais são para desenvolvimento e não devem ser reutilizadas em produção. Em seguida, compile e inicie os serviços:

```bash
./local-infra/scripts/start.sh
```

Abra [http://127.0.0.1:8069](http://127.0.0.1:8069). No primeiro acesso, o Odoo exibirá o gerenciador de bancos de dados. Crie um banco de dados e informe o valor de `ODOO_ADMIN_PASSWD` como senha mestra. O acesso de usuário à aplicação Odoo é criado durante a configuração do banco de dados e é diferente da senha mestra do gerenciador.

Na primeira execução, o script de inicialização também pode criar o arquivo de ambiente e encerrar exibindo as instruções. Assim, credenciais de exemplo nunca são aceitas silenciosamente.

## Comandos do dia a dia

Todos os scripts podem ser executados a partir de qualquer diretório atual; os caminhos são resolvidos com base no local do próprio script.

```bash
./local-infra/scripts/start.sh       # compila, se necessário, e inicia PostgreSQL + Odoo
./local-infra/scripts/status.sh      # mostra o estado dos serviços e as portas publicadas
./local-infra/scripts/logs.sh        # acompanha os registros dos dois serviços
./local-infra/scripts/logs.sh odoo   # acompanha somente os registros do Odoo
./local-infra/scripts/logs.sh db     # acompanha somente os registros do PostgreSQL
./local-infra/scripts/stop.sh        # para e remove contêineres/rede, preservando os volumes nomeados
./local-infra/scripts/db-ide.sh start  # inicia somente o PostgreSQL para conectar pelo JetBrains
./local-infra/scripts/db-ide.sh status # mostra o estado e os parâmetros da conexão JetBrains
```

Para iniciar novamente após parar os serviços, execute `start.sh`. Para recompilar explicitamente a imagem do Odoo, execute `start.sh` (o comando usa `compose up --build`).

## Dados e redefinição

O Compose cria os volumes nomeados `voigt-odoo-local_postgres-data` e `voigt-odoo-local_odoo-data` (os nomes efetivos podem ser consultados com `docker volume ls`). O PostgreSQL armazena seu cluster no primeiro; o Odoo armazena os arquivos da aplicação e outros dados de execução no segundo. `stop.sh` preserva ambos. Para apagar intencionalmente os dois volumes e voltar a uma instância local vazia:

```bash
./local-infra/scripts/reset.sh
```

O script de redefinição solicita que você digite `DELETE` e, em seguida, remove os contêineres e volumes. Essa ação não pode ser desfeita. Faça cópias de segurança dos dados locais que deseja manter antes de confirmar.

## Configuração

Edite `local-infra/.env` (ignorado pelo Git):

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `POSTGRES_DB` | `postgres` | Banco de dados inicial criado pela imagem do PostgreSQL; o gerenciador de bancos do Odoo pode criar outros bancos. |
| `POSTGRES_USER` | `odoo` | Usuário de banco usado pelo Odoo. Evite usar o superusuário do PostgreSQL. |
| `POSTGRES_PASSWORD` | obrigatório | Senha do usuário acima. |
| `ODOO_ADMIN_PASSWD` | obrigatório | Senha mestra do gerenciador de bancos do Odoo, gravada pelo entrypoint existente em um arquivo temporário de configuração com permissão 0600. |
| `ODOO_BIND_ADDRESS` | `127.0.0.1` | Interface de rede do computador na qual o Odoo será disponibilizado. Por padrão, o acesso pela rede local fica bloqueado. |
| `ODOO_PORT` | `8069` | Porta do computador mapeada para a porta 8069 do contêiner. |
| `DB_IDE_BIND_ADDRESS` | `127.0.0.1` | Endereço local do computador no qual a porta PostgreSQL será publicada para a IDE. Mantenha em `127.0.0.1` para que o banco não fique acessível pela rede. |
| `DB_IDE_PORT` | `15432` | Porta do computador mapeada para a porta PostgreSQL 5432 do contêiner. A porta 15432 evita conflitar com instalações locais comuns do PostgreSQL. |
| `ODOO_SOURCE_REV` | `local-uncommitted` | Identificação da revisão do código na imagem. Quando possível, `start.sh` substitui esse valor padrão pela revisão curta atual do Git. |

Ao alterar credenciais de um banco de dados já inicializado, o PostgreSQL não atualiza a senha do usuário armazenada no volume existente. Se a instância de desenvolvimento puder ser descartada, execute `reset.sh` e inicie novamente. Caso contrário, altere a senha do usuário do banco no PostgreSQL para que corresponda ao novo valor no arquivo de ambiente.

## Arquitetura e limites

- O projeto Compose se chama `voigt-odoo-local`; todas as definições, o modelo de configuração, os scripts e a documentação ficam neste diretório.
- O contexto de compilação é a raiz do repositório porque o Dockerfile existente copia dali o código-fonte e as dependências do Odoo. O Compose aponta diretamente para esse Dockerfile; a infraestrutura local não mantém uma versão própria do processo de compilação da aplicação.
- O PostgreSQL 16 é um serviço separado em uma rede bridge privada. Sua porta é publicada apenas no endereço local `127.0.0.1:15432` por padrão, para conexão do JetBrains Database Tools; ela não fica acessível pela rede. Para administração local, use `docker compose exec db psql -U odoo`.
- O script `db-ide.sh start` inicia somente o PostgreSQL e aguarda sua verificação de saúde; ele não inicia, altera nem depende da configuração AWS/cloud.
- O Odoo aguarda o PostgreSQL indicar que está pronto. A verificação de saúde do PostgreSQL usa `pg_isready`; a condição `service_healthy` do Compose controla quando o Odoo pode iniciar.
- Somente a porta HTTP do Odoo é publicada e, a menos que seja alterada deliberadamente, fica vinculada ao endereço local do computador.
- Os serviços usam políticas de reinicialização e um período de um minuto para encerramento normal. O contêiner do Odoo mantém o UID não privilegiado 10001 definido na imagem e usa o entrypoint existente.

## Uso direto do Compose

Os scripts são atalhos convenientes. A partir de qualquer diretório:

```bash
docker compose --project-directory "$PWD/local-infra" \
  --env-file "$PWD/local-infra/.env" \
  -f "$PWD/local-infra/compose.yaml" ps
```

Use os scripts, a menos que precise executar uma operação pontual do Compose. `docker compose config` pode exibir credenciais após interpolar as variáveis; não copie essa saída para registros ou chamados de suporte.

## Conectar o JetBrains Database Tools ao PostgreSQL local

O acesso usado pela IDE é o banco do Docker Compose local. Ele é independente do túnel AWS/Kubernetes `odoo-db-tunnel.sh` presente no outro repositório. Não execute nem altere aquele túnel para usar o banco local; esta configuração não modifica arquivos, fontes de dados ou credenciais cloud.

### Iniciar somente o banco local

Na raiz deste repositório, execute:

```bash
./local-infra/scripts/db-ide.sh start
```

O script usa `local-infra/.env`, inicia somente o serviço `db`, aguarda o PostgreSQL ficar saudável e imprime os parâmetros da IDE. O Odoo pode estar parado. Se a stack completa já estiver ativa, o comando mantém o banco em execução.

Para consultar os parâmetros sem iniciar serviço algum:

```bash
./local-infra/scripts/db-ide.sh status
```

### Criar a fonte de dados na IDE

No DataGrip ou nas ferramentas de banco integradas do IntelliJ IDEA:

1. Abra a janela **Database** e escolha **+ > Data Source > PostgreSQL**.
2. Na aba **General**, preencha os campos abaixo com os valores de `local-infra/.env`:

   | Campo da IDE | Valor local padrão |
   | --- | --- |
   | Name | `Voigt Odoo Local` (nome livre para a conexão local) |
   | Host | `127.0.0.1` (`DB_IDE_BIND_ADDRESS`) |
   | Port | `15432` (`DB_IDE_PORT`) |
   | User | valor de `POSTGRES_USER` (padrão `odoo`) |
   | Password | valor de `POSTGRES_PASSWORD` |
   | Database | valor de `POSTGRES_DB` (padrão `postgres`) |

3. Selecione **Save** para a senha ficar armazenada no IDE conforme a política de senhas configurada nele. Não coloque a senha no campo URL.
4. Clique em **Test Connection**. Se a IDE solicitar, baixe o driver PostgreSQL sugerido.
5. Após o teste bem-sucedido, clique em **Apply** e **OK**. A conexão local aparecerá na janela **Database**.

A URL JDBC equivalente é `jdbc:postgresql://127.0.0.1:15432/postgres` com os valores padrão. Se alterar `DB_IDE_PORT`, `DB_IDE_BIND_ADDRESS` ou `POSTGRES_DB`, use os novos valores. A senha de conexão é `POSTGRES_PASSWORD`; `ODOO_ADMIN_PASSWD` é a senha mestra do gerenciador do Odoo e **não** deve ser usada como senha PostgreSQL.

### Usar a conexão sem iniciar o Odoo

O PostgreSQL pode ser iniciado de forma independente para inspeção ou administração do banco. A primeira inicialização cria somente o banco inicial `postgres`; um banco Odoo aparecerá depois que for criado pelo gerenciador do Odoo. Para trabalhar com um banco específico, escolha-o no campo **Database** ou na árvore da fonte de dados.

Para parar os serviços, `./local-infra/scripts/stop.sh` para Odoo e PostgreSQL, removendo os contêineres mas preservando os dados. O comando **Disconnect** na IDE encerra somente a sessão do cliente, não o banco. A rotina `reset.sh` apaga os dados locais e pode invalidar a conexão configurada se as credenciais forem alteradas.

### Isolamento da conexão cloud

- Dê à fonte de dados local um nome distinto, como `Voigt Odoo Local`; não sobrescreva nem renomeie a fonte `voigt odoo` usada para cloud.
- A conexão local usa `127.0.0.1:15432`, publicado pelo Compose. O túnel cloud de referência usa a mesma porta enquanto está ativo, portanto os dois processos não conseguem escutar nela ao mesmo tempo. Para alternar entre eles, pare o túnel cloud antes de iniciar o banco local ou escolha outra porta para `DB_IDE_PORT` e configure-a na fonte local. A fonte local não deve apontar para o túnel cloud.
- O endereço de publicação padrão é loopback. Não o altere para `0.0.0.0` sem necessidade, pois isso pode expor o banco na rede do computador.
- O arquivo `.env` local e as configurações cloud permanecem separados. Este diretório não lê o `.env` do Pulumi nem executa scripts AWS.

## Solução de problemas

- Erro ao acessar o daemon do Docker: inicie o Docker Desktop ou o Docker Engine e execute o comando novamente.
- Porta ocupada: defina outro valor para `ODOO_PORT` em `.env` e reinicie os serviços.
- A IDE não conecta: execute `scripts/db-ide.sh status`, confira se `db` está saudável, confirme host/porta/usuário/senha e verifique se outro processo (por exemplo, o túnel cloud) está usando a porta configurada.
- O Odoo não consegue se conectar: consulte `scripts/logs.sh db` e `scripts/logs.sh odoo`; aguarde até que o serviço `db` esteja saudável.
- Problemas de acesso ou inicialização: confira a senha do gerenciador de bancos e as credenciais do banco. Se as credenciais ou os dados do banco estiverem inconsistentes e os dados puderem ser descartados, redefina os volumes.
- Contexto de compilação muito grande: o `.dockerignore` da raiz exclui diretórios de configuração, documentação e testes. Ele mantém disponíveis o código-fonte da aplicação e os arquivos usados pelo Dockerfile existente.

## Relatório dos artefatos e justificativas

| Artefato | Função e justificativa |
| --- | --- |
| `compose.yaml` | Declara os serviços isolados PostgreSQL e Odoo, o vínculo da compilação com o Dockerfile existente na raiz, a rede privada, os volumes nomeados, a verificação de saúde, a publicação de porta e o encerramento normal em uma definição Compose portátil. |
| `.env.example` | Documenta valores padrão seguros para uso local e as credenciais obrigatórias sem incluir segredos no repositório. O vínculo ao endereço local evita exposição acidental. |
| `.gitignore` | Impede que o arquivo `.env` gerado, que contém credenciais, seja incluído no controle de versão. |
| `scripts/lib.sh` | Centraliza a localização dos caminhos, a verificação de pré-requisitos, a validação do ambiente e a chamada do Compose para manter os scripts consistentes. |
| `scripts/setup.sh` | Cria o arquivo de ambiente local com permissões restritivas antes da inicialização. |
| `scripts/start.sh` | Verifica os pré-requisitos e as credenciais, registra a revisão do código-fonte quando possível e compila e inicia todos os serviços. |
| `scripts/stop.sh` | Para os serviços preservando os volumes nomeados, conforme o uso normal esperado em desenvolvimento local. |
| `scripts/status.sh` | Mostra rapidamente o estado dos serviços e as portas sem exigir que a pessoa memorize opções do Compose. |
| `scripts/logs.sh` | Acompanha os registros de todos os serviços ou de um serviço específico, aceitando nomes de serviço opcionais. |
| `scripts/reset.sh` | Permite retornar deliberadamente a uma instância vazia, com confirmação explícita porque a exclusão dos volumes nomeados é destrutiva. |
| `scripts/db-ide.sh` | Inicia somente o PostgreSQL ou exibe seu estado e os parâmetros necessários para configurar a fonte de dados JetBrains. Permite usar o banco local sem chamar a infraestrutura AWS. |
| `README.md` | Explica a configuração inicial, o uso diário, a arquitetura, a configuração, a persistência, a recuperação e a justificativa de cada artefato gerado. |

## Referências externas utilizadas

- Ordem de inicialização no Docker Compose: o Compose aguarda a verificação de saúde de uma dependência quando `depends_on` usa a condição `service_healthy`. [Documentação do Docker](https://docs.docker.com/compose/how-tos/startup-order)
- Definições de serviços e volumes do Docker Compose: [referência de serviços do Compose](https://docs.docker.com/reference/compose-file/services/) e [guia de início rápido do Compose](https://docs.docker.com/compose/gettingstarted/).
- O Odoo requer PostgreSQL e deve se conectar usando um usuário dedicado, em vez do superusuário do PostgreSQL. [Documentação de instalação do Odoo](https://www.odoo.com/documentation/saas-15.4/administration/install/install.html).

A página de instalação do Odoo é antiga e específica de uma versão anterior. O requisito do PostgreSQL e a recomendação de usar um usuário dedicado continuam aplicáveis; o comportamento em tempo de execução descrito aqui foi baseado no Dockerfile e no entrypoint deste repositório.
