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
./local-infra/scripts/start-ide.sh    # inicia somente o PostgreSQL necessário ao runner IntelliJ
./local-infra/scripts/stop-ide.sh     # para somente o PostgreSQL, preservando os dados
./local-infra/scripts/setup-ide.sh     # prepara o ambiente Python para executar/debugar pelo IntelliJ
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
- O código de suporte exclusivo da IDE fica em `local-infra/ide-runner/`, fora das pastas oficiais `odoo/` e `addons/`. Os scripts operacionais ficam em `local-infra/scripts/`; a configuração compartilhada do IntelliJ fica em `.idea/runConfigurations/`. Essa separação mantém os artefatos auxiliares fora do código da plataforma e deixa explícito que eles não fazem parte do pacote Odoo nem da imagem cloud.
- O runner não copia nem modifica o `odoo-bin`: ele delega a execução ao arquivo oficial na raiz do projeto. Só a inicialização acontece por meio do wrapper de desenvolvimento, que valida o PostgreSQL e impede dois servidores Odoo simultâneos.
- O `.dockerignore` exclui `local-infra/`, `.idea/`, `.run/` e `.venv/` do contexto de compilação. Embora o Dockerfile use o contexto raiz para acessar o código Odoo, os arquivos de suporte da IDE não são copiados para a imagem.
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

## Executar, depurar e testar Odoo pelo IntelliJ IDEA

O projeto inclui uma configuração compartilhada em `.idea/runConfigurations/Voigt_Odoo_IDE.xml`, chamada **Voigt Odoo Local (IDE Debug/Test)**. Ela inicia o `odoo-bin` como processo Python local, permitindo usar os breakpoints e ferramentas de depuração/teste do IntelliJ. A aplicação usa o PostgreSQL local do Compose em `127.0.0.1:15432`; não usa o PostgreSQL cloud.

O plugin **Odoo** mostrado nas configurações da IDE permanece habilitado e complementa o trabalho com o código: segundo a descrição do plugin e o projeto oficial OdooLS, ele fornece recursos de linguagem, como informações ao passar o mouse, navegação para definições, autocompletar e diagnósticos. Ele não inicia o servidor Odoo nem configura o debugger Python. Por isso, o projeto mantém uma configuração de execução Python separada; os recursos do plugin continuam disponíveis no editor durante a execução e depuração.

### Preparar o interpretador e as credenciais locais

Esta preparação é executada uma vez por checkout (e novamente quando os requisitos Python mudarem):

1. Confirme que `local-infra/.env` está preenchido, como descrito em [Primeira execução](#primeira-execução).
2. Instale os pacotes nativos listados abaixo. O host precisa de privilégios administrativos para essa etapa:

   ```bash
   sudo apt-get update
   sudo apt-get install -y build-essential libffi-dev libfreetype6-dev libfribidi-dev libharfbuzz-dev libjpeg62-turbo-dev libldap2-dev liblcms2-dev libmagic-dev libopenjp2-7-dev libpq-dev libsasl2-dev libssl-dev libtiff-dev libwebp-dev libxcb1-dev libxml2-dev libxslt1-dev pkg-config zlib1g-dev
   ```

3. Prepare o interpretador virtual isolado e as credenciais locais:

   ```bash
   ./local-infra/scripts/setup-ide.sh
   ```

   O script cria `.venv` na raiz e instala as dependências de `requirements.txt`, respeitando `constraints-voigt.txt`. Cria também `local-infra/.pgpass` e `local-infra/.local/ide-odoo.conf`, ambos com permissão 0600. Esses arquivos contêm credenciais locais e são ignorados pelo Git.

   O runner usa Python 3.12 e as versões de dependências/restrições definidas neste repositório; as bibliotecas nativas do sistema são fornecidas pelo computador host.

4. No IntelliJ IDEA, confirme que o plugin Python está habilitado e selecione `$PROJECT_DIR$/.venv/bin/python` como interpretador do projeto. A configuração compartilhada já aponta para esse caminho.

### Iniciar e depurar a aplicação

1. Confirme que o Docker está ativo e que a aplicação Odoo em Compose está parada. Se o serviço `odoo` estiver em execução, pare somente esse serviço:

   ```bash
   docker compose --project-directory local-infra --env-file local-infra/.env -f local-infra/compose.yaml stop odoo
   ```

2. No seletor de configurações do IntelliJ, escolha **Voigt Odoo Local (IDE Debug/Test)** e clique em **Run** ou **Debug**. Não é necessário executar `start-ide.sh` antes: o wrapper prepara os arquivos privados locais e inicia automaticamente somente o serviço PostgreSQL `db`, se ele ainda não estiver ativo.
3. A configuração usa HTTP em `127.0.0.1:8070`, separado da porta 8069 do serviço Odoo em container. Acesse [http://127.0.0.1:8070](http://127.0.0.1:8070). Defina breakpoints no código Python do Odoo ou dos addons e use o painel **Debug** para inspecionar a execução.
4. Ao terminar, use **Stop** na janela Run/Debug. O PostgreSQL continua ativo para manter a conexão do Database Tools e evitar inicializações repetidas. Quando quiser pará-lo também, execute `./local-infra/scripts/stop-ide.sh`.

### Pré-etapas automatizadas ao clicar em Run/Debug

O `local-infra/ide-runner/odoo_ide_runner.py` executa essas verificações antes de chamar o `odoo-bin` oficial:

1. Cria um marcador PID local para impedir que os scripts Compose parem ou iniciem serviços enquanto a depuração estiver ativa.
2. Lê `local-infra/.env` e gera/atualiza `.pgpass` e `ide-odoo.conf` com permissões 0600. A senha não fica na configuração versionada do IntelliJ.
3. Verifica se o Odoo em container está ativo; se estiver, encerra com uma instrução de como alternar os modos.
4. Executa `docker compose up --detach --wait db`: somente o PostgreSQL é criado/iniciado; não sobe o serviço `odoo` da Compose.
5. Confirma a saúde com `pg_isready` e testa a porta TCP publicada.
6. Inicia o `odoo-bin` a partir do código oficial da raiz, com o interpretador `.venv` e o debugger do IntelliJ.

Se uma etapa falhar, o wrapper encerra e remove o marcador PID. Os scripts `start.sh`, `stop.sh`, `reset.sh`, `start-ide.sh` e `stop-ide.sh` verificam esse marcador para proteger a sessão da IDE.

O runner `local-infra/ide-runner/odoo_ide_runner.py` verifica que o serviço `db` está acessível e interrompe a inicialização se o serviço `odoo` do Compose estiver rodando. O script cria um marcador local de PID enquanto o runner está ativo; `start.sh`, `stop.sh`, `reset.sh`, `start-ide.sh` e `stop-ide.sh` consultam esse marcador para evitar iniciar ou desligar serviços Compose durante a sessão de depuração. Portanto, os dois processos Odoo não atendem simultaneamente nem disputam os mesmos registros do banco.

Para alternar para o Odoo em container, pare a configuração da IDE e execute `./local-infra/scripts/start.sh`. Para voltar à IDE, pare o Odoo em container sem parar o PostgreSQL e então inicie o runner:

```bash
docker compose --project-directory local-infra --env-file local-infra/.env -f local-infra/compose.yaml stop odoo
./local-infra/scripts/start-ide.sh
```

Ao terminar o trabalho na IDE, pare o runner pelo botão **Stop** e execute `./local-infra/scripts/stop-ide.sh` para parar somente o PostgreSQL, preservando os dados. A verificação impede parar o banco se o runner ou o Odoo em Compose ainda estiver ativo.

O runner da IDE usa um diretório de dados/filestore próprio em `local-infra/data/ide-runner`, separado do volume `odoo-data` do container. O banco PostgreSQL é compartilhado, mas arquivos de anexos/filestore escritos por um processo não são automaticamente copiados para o outro. Para depurar fluxos que dependem de anexos já existentes, use a aplicação em container ou copie os dados de filestore de forma deliberada antes da execução.

### Executar testes do Odoo

Use **Run** ou **Debug** na mesma configuração Python; o IntelliJ mantém suporte a breakpoints durante a execução dos testes. Edite temporariamente **Program arguments** na configuração (ou duplique a configuração para manter uma variante de testes) para indicar um banco de teste e as opções do Odoo. Exemplo de execução de testes de um módulo:

```text
-d voigt_odoo_test -i sale --test-enable --test-tags /sale --stop-after-init
```

O banco `voigt_odoo_test` deve existir no PostgreSQL local. Use um banco descartável para testes: algumas suítes instalam módulos, criam registros e podem alterar os dados. `-i sale` instala/atualiza o módulo indicado antes dos testes; ajuste o nome do módulo e os `--test-tags` para seu caso. Remova os argumentos de teste para voltar a iniciar o servidor web de depuração. A configuração padrão não executa testes automaticamente.

### Credenciais e ajustes locais

- A senha PostgreSQL é lida pelo libpq a partir de `local-infra/.pgpass`; ela não fica escrita na configuração compartilhada do IntelliJ.
- `ODOO_ADMIN_PASSWD` é gravada apenas no arquivo local `local-infra/.local/ide-odoo.conf`, necessário para o gerenciador de bancos do Odoo.
- A configuração `.run`/`.idea` rastreada contém somente caminhos relativos, portas, nome do usuário padrão e parâmetros não secretos. Se personalizar `DB_IDE_PORT` ou `POSTGRES_USER` em `.env`, atualize os valores correspondentes em `PGPORT` e `PGUSER` nessa configuração compartilhada.
- `setup-ide.sh` instala as dependências e prepara as credenciais. A cada execução do runner, os arquivos `.pgpass` e `ide-odoo.conf` são atualizados automaticamente para refletir o `.env` local.
- O interpretador `.venv` fica fora do código Odoo oficial e da imagem Docker; ele pode ser recriado removendo `.venv` e executando `setup-ide.sh` novamente.

### Por que a configuração fica no repositório

O JetBrains permite salvar configurações compartilhadas como arquivos do projeto; o local padrão é `.idea/runConfigurations`. O `.gitignore` deste repositório ignora arquivos privados do IntelliJ, mas abre exceção somente para arquivos XML nessa subpasta. Assim, o runner pode ser distribuído com o projeto sem versionar configurações pessoais, credenciais, histórico da IDE ou fontes de dados locais.

## Solução de problemas

| Sintoma | Causa provável | Efeito | Ação |
| --- | --- | --- | --- |
| Runner informa que Docker não pode ser consultado | Docker Desktop/Engine está parado ou o usuário não tem acesso ao daemon. | O PostgreSQL não inicia e o Odoo IDE não é executado. | Inicie o Docker e confirme `docker info`; depois use Run/Debug novamente. |
| `setup-ide.sh` para em `pg_config` ou dependências nativas | Pacotes de desenvolvimento do host estão ausentes. | O `.venv` não recebe todas as dependências do Odoo. | Instale o conjunto de pacotes do passo de preparação e execute `setup-ide.sh` novamente. |
| IntelliJ diz que o interpretador `.venv/bin/python` não existe | Preparação do ambiente não foi executada ou `.venv` foi removido. | A configuração Python não consegue iniciar. | Execute `./local-infra/scripts/setup-ide.sh` e selecione novamente o interpretador se necessário. |
| Runner diz que faltam `POSTGRES_PASSWORD` ou `ODOO_ADMIN_PASSWD` | `.env` não existe ou ainda tem valores de exemplo. | Credenciais não são materializadas; o processo para antes de subir o banco. | Execute `setup.sh`, preencha `local-infra/.env` e tente de novo. |
| Runner informa que Odoo Compose está ativo | O container `odoo` ainda está rodando. | O wrapper interrompe a inicialização para evitar dois servidores usando o mesmo banco. | Pare a configuração IDE e então use `docker compose ... stop odoo` antes de rodar a IDE; ou pare o runner e use `start.sh` para Compose. |
| PostgreSQL não fica saudável durante Run/Debug | Inicialização do container falhou, volume está inconsistente ou a porta do host está ocupada. | O wrapper não chama `odoo-bin`. | Consulte `./local-infra/scripts/logs.sh db`, verifique `./local-infra/scripts/db-ide.sh status` e escolha outra `DB_IDE_PORT` se houver conflito. |
| Erro de conexão TCP para `127.0.0.1:15432` | A porta foi alterada, está ocupada pelo túnel cloud ou não foi publicada. | O `pg_isready` interno pode passar, mas o host/IDE não acessa o banco. | Confira `.env`, pare o túnel cloud se usar a mesma porta, ajuste `PGPORT` na configuração IntelliJ e execute novamente. |
| O IDE informa senha PostgreSQL inválida | `.env` mudou após a criação do volume, ou a senha no volume é antiga. | O Odoo e o Database Tools não autenticam. | Para dados descartáveis, use `reset.sh`; para preservar dados, altere a senha da role PostgreSQL para o valor do `.env`. |
| Script diz que outro runner está ativo ou `stop-ide.sh` recusa parar | A configuração Python ainda está rodando ou sobrou um PID obsoleto. | Scripts de infraestrutura se recusam a desligar o banco durante depuração. | Pare o processo pelo botão Stop. Se ele já encerrou, confira `.local/ide-runner.pid`; remova somente se o PID não existir. |
| Odoo inicia mas não encontra anexos antigos | Runner e container usam diretórios de filestore diferentes. | Registros do banco aparecem, mas os arquivos armazenados podem faltar. | Use o modo container para fluxos com anexos existentes ou copie o filestore deliberadamente antes de depurar. |
| Configuração não aparece no IntelliJ | Arquivo XML não foi carregado ou plugin Python está desabilitado. | A configuração não aparece no seletor Run/Debug. | Confirme `.idea/runConfigurations/Voigt_Odoo_IDE.xml`, habilite Python e reabra o projeto. |
| Testes não encontram o banco informado | `-d` aponta para um banco ainda não criado ou módulos requeridos não estão instalados. | Odoo encerra antes de executar os testes. | Crie um banco de teste descartável e instale o módulo com `-i`; mantenha `--test-enable --stop-after-init`. |

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
| `scripts/start-ide.sh` | Atalho explícito para iniciar somente o PostgreSQL e aguardar sua saúde, sem subir o serviço Odoo em container. |
| `scripts/stop-ide.sh` | Para somente o PostgreSQL, preservando volumes, e recusa parar enquanto o Odoo em container ou o runner IDE estiver ativo. |
| `scripts/setup-ide.sh` | Prepara o virtualenv Python e materializa credenciais somente locais com permissões restritivas para o runner do IntelliJ. |
| `ide-runner/odoo_ide_runner.py` | Código auxiliar isolado fora das pastas oficiais da plataforma. Cria credenciais locais, verifica os serviços Compose, mantém um marcador de PID, inicia somente o PostgreSQL se necessário e delega a inicialização ao `odoo-bin` oficial no processo depurável da IDE. |
| `ide-runner/prepare_ide_files.py` | Compartilha a leitura do `.env` e a criação atômica dos arquivos `.pgpass` e `ide-odoo.conf` entre a preparação inicial e cada execução, mantendo permissões restritivas sem duplicar lógica. |
| `.idea/runConfigurations/Voigt_Odoo_IDE.xml` | Configuração compartilhada Python do IntelliJ, com interpretador do projeto, caminho do runner, conexão PostgreSQL local e porta HTTP alternativa. Não contém senhas. |
| `.gitignore` (raiz) | Mantém arquivos pessoais do IntelliJ ignorados, liberando para versionamento somente as configurações compartilhadas XML em `.idea/runConfigurations`. |
| `.dockerignore` | Exclui toda a infraestrutura local, a configuração IntelliJ e o virtualenv do contexto enviado ao Docker, evitando incorporar artefatos de desenvolvimento à imagem Odoo. |
| `local-infra/.gitignore` | Exclui credenciais PostgreSQL, configuração gerada do runner e dados locais do filestore. |
| `README.md` | Explica a configuração inicial, o uso diário, a arquitetura, a configuração, a persistência, a recuperação e a justificativa de cada artefato gerado. |

## Referências externas utilizadas

- Ordem de inicialização no Docker Compose: o Compose aguarda a verificação de saúde de uma dependência quando `depends_on` usa a condição `service_healthy`. [Documentação do Docker](https://docs.docker.com/compose/how-tos/startup-order)
- Definições de serviços e volumes do Docker Compose: [referência de serviços do Compose](https://docs.docker.com/reference/compose-file/services/) e [guia de início rápido do Compose](https://docs.docker.com/compose/gettingstarted/).
- O Odoo requer PostgreSQL e deve se conectar usando um usuário dedicado, em vez do superusuário do PostgreSQL. [Documentação de instalação do Odoo](https://www.odoo.com/documentation/saas-15.4/administration/install/install.html).
- Configurações de execução compartilhadas do IntelliJ podem ser armazenadas como arquivos do projeto; o padrão é `.idea/runConfigurations`. [Documentação de Run/Debug Configurations do IntelliJ IDEA](https://www.jetbrains.com/help/idea/run-debug-configuration.html).
- O JetBrains oferece intérpretes Python locais e remotos via Docker/Compose; este runner escolhe um interpretador local para permitir depuração Python direta do processo. [Configurar um interpretador Python](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html).
- O plugin oficial OdooLS para PyCharm fornece recursos do servidor de linguagem, incluindo informações contextuais, navegação, autocompletar e diagnósticos. [Repositório oficial Odoo para o plugin](https://github.com/odoo/odoo-pycharm) e [guia de uso do OdooLS](https://github.com/odoo/odoo-ls/wiki/2.-How-to-use).

A página de instalação do Odoo é antiga e específica de uma versão anterior. O requisito do PostgreSQL e a recomendação de usar um usuário dedicado continuam aplicáveis; o comportamento em tempo de execução descrito aqui foi baseado no Dockerfile e no entrypoint deste repositório.
