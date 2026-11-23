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

## Como executar os scripts wrapper

Os wrappers agrupam as etapas dos guias manuais: use o primeiro uma vez por checkout e o segundo a cada sessão de trabalho. Execute os comandos a partir da raiz do repositório, como nos exemplos abaixo; os scripts também resolvem os caminhos a partir da própria localização.

### Primeira configuração deste checkout

```bash
./local-infra/scripts/ide-first-run.sh
```

O script cria `local-infra/.env` se ainda não existir. Na primeira chamada, ele para para você editar o arquivo e substituir `POSTGRES_PASSWORD` e `ODOO_ADMIN_PASSWD`; depois de salvar, execute o mesmo comando novamente. O host precisa ter Python 3.12 e `venv` disponíveis; o wrapper não instala nem atualiza o interpretador global. Em hosts Debian/Ubuntu/Pop!_OS, identifica o codinome do sistema, verifica dependências com uma simulação do APT direcionada a essa versão e baixa, sem instalar no sistema, os pacotes de desenvolvimento e as bibliotecas de runtime necessárias. Isso inclui dependências transitivas resolvidas pelo APT. Os arquivos `.deb` são extraídos para uma área privada em `local-infra/.local/native`; o bootstrap Python usa somente para o processo da IDE os caminhos de bibliotecas, headers, linker e `pkg-config` dessa área. Nomes que variam entre versões têm alternativas equivalentes, como `libfreetype-dev`/`libfreetype6-dev` e `libjpeg-turbo8-dev`/`libjpeg62-turbo-dev`/`libjpeg-dev`. Arquivos estáticos `.a` são removidos do prefixo para evitar que o linker escolha uma biblioteca estática incompatível ao construir extensões compartilhadas. Em seguida prepara `.venv`, sincroniza os requisitos do Odoo e cria as credenciais locais protegidas. Repetir o script reutiliza o prefixo compatível já criado e não altera os pacotes de sistema.

O script executa `apt-get update` para atualizar somente os índices de pacotes e usa `sudo` para baixar os arquivos. A chamada APT usa `--download-only`; os arquivos de download passam por uma pasta temporária acessível ao sandbox APT em `/tmp`, depois são extraídos para o prefixo do projeto. O script não executa uma instalação efetiva via APT/dpkg, não chama `ldconfig` e não altera bibliotecas em `/usr` nem o banco de pacotes instalado do host. A simulação e o download são limitados ao codinome do sistema; se não houver uma solução compatível, o wrapper para antes de trocar o link do prefixo local. Os prefixos são montados em uma pasta temporária e ativados por troca atômica de link simbólico, para evitar uma atualização parcial. Se a simulação encontrar versões incompatíveis, corrija as fontes APT da máquina antes de tentar novamente. O manual do APT explica a seleção de versões por prioridades e a documentação Ubuntu explica o gerenciamento de fontes ([APT](https://manpages.ubuntu.com/manpages/noble/man5/apt_preferences.5.html), [fontes Ubuntu](https://help.ubuntu.com/stable/ubuntu-help/addremove-sources.html)).

### Uso diário

```bash
./local-infra/scripts/ide-day.sh
```

Esse script confirma que o Docker está disponível, repete as verificações idempotentes de preparação, para somente o serviço `odoo` em Compose se estiver rodando e inicia somente o PostgreSQL. Depois, no IntelliJ, selecione **Voigt Odoo Local (IDE Debug/Test)** e clique em **Run** ou **Debug**. O script não abre nem inicia a interface gráfica do IntelliJ. Ao encerrar, use **Stop** na IDE; o banco continua ativo. Execute `./local-infra/scripts/stop-ide.sh` quando quiser parar também o PostgreSQL. Se preferir executar cada etapa manualmente, siga os dois guias abaixo.

Se a preparação inicial for chamada antes de preencher as senhas, o script encerra sem iniciar serviços e informa para editar `.env` e executar novamente. A atualização dos índices APT e o download dos arquivos locais podem pedir autenticação via `sudo`; os pacotes não são instalados globalmente.

Para remover somente a cópia isolada das bibliotecas nativas, pare antes o runner IntelliJ e apague `local-infra/.local/native`. Não apague toda a pasta `.local`, pois ela também contém configuração privada do Odoo. O próximo `ide-first-run.sh` baixa e monta novamente o prefixo. Isso não remove nem altera bibliotecas do sistema.

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

## Versões de referência e compatibilidade entre computadores

Esta tabela registra o ambiente de referência observado em **23/11/2026**. Ela separa os valores definidos pelo repositório dos valores da máquina usada para validar esta configuração. Os valores do host e da IDE são informativos; em outro computador, registre os resultados dos comandos abaixo e gere novamente os artefatos locais.

| Componente | Versão/referência | Origem e como interpretar |
| --- | --- | --- |
| Sistema host de referência | Pop!_OS 24.04 LTS, base Ubuntu Noble (`noble`), arquitetura `x86_64` | Detectado em `/etc/os-release` e `uname -m`. O script usa o codinome do host para selecionar pacotes nativos; este valor não é fixo no projeto. |
| Ferramentas do host usadas no bootstrap | GNU Bash 5.2.21, APT 2.8.4, dpkg 1.22.6, GCC 13.3.0 e pkg-config 1.8.1 | Versões observadas no host de referência. O bootstrap requer Bash, APT/dpkg, GCC e pkg-config compatíveis; distribuições suportadas podem fornecer versões diferentes. Os pacotes nativos resolvidos em cada host ficam registrados em `local-infra/.local/native/current/packages.tsv`. |
| Python do host e da `.venv` | Python 3.12.3 no host de referência | Detectado por `python3.12 --version`. O projeto exige a série 3.12 para o runner; o patch pode variar por computador. O wrapper não instala nem atualiza Python globalmente. |
| Docker Engine | 29.10.0 no host de referência | Detectado por `docker --version`; instalado e atualizado fora deste repositório. |
| Docker Compose | Plugin Compose v5.7.1 no host de referência | Detectado por `docker compose version`. O pré-requisito do projeto é o comando `docker compose`; o script não fixa uma versão mínima numérica e usa o plugin instalado junto ao Docker do host. |
| IntelliJ IDEA | 2026.3, build `IU-263.7307.200` no host de referência | Detectado por `idea --version`. A configuração compartilhada fica em `.idea/runConfigurations/Voigt_Odoo_IDE.xml`, mas o IDE não é instalado nem fixado pelo projeto. |
| Plugin Odoo para IntelliJ | 1.6.2, conforme a tela de Plugins fornecida | Plugin habilitado na IDE de referência. A versão não é fixada pelo XML do runner; confirme compatibilidade/atualizações pelo Marketplace da instalação IntelliJ. |
| Plugin Python da IntelliJ | Habilitado no IDE de referência | O projeto depende do suporte a SDKs e configurações Python; a versão do plugin acompanha a instalação do IntelliJ e não é fixada no repositório. |
| Database Tools e Drivers da IntelliJ | Recurso disponível na IDE de referência | A fonte PostgreSQL é uma configuração pessoal da IDE; o repositório documenta host/porta/usuário, mas não fixa a versão do plugin nem compartilha senhas. |
| Odoo do checkout | Série 20.0; `odoo/release.py` informa 20.0.0 | Versão da árvore de código atual, não uma versão de imagem Odoo publicada. O runner IntelliJ chama o `odoo-bin` oficial deste checkout. |
| PostgreSQL do Compose | Imagem `postgres:16-bookworm`; digest local observado `sha256:ce3efec6bc404f6b15ebf5d9bed6b45a9d4655aea238d7dacc3467ccb05a1175` | A definição Compose fixa a série 16 e a família Debian Bookworm pela tag, mas não fixa o digest. O digest citado é o que estava no cache Docker deste host em 23/11/2026; em outra máquina, `docker image inspect` pode mostrar um digest mais recente. |
| Base Python da imagem Odoo | `python:3.12-slim-bookworm`, digest `sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70` | Fixado por digest no `Dockerfile`. A imagem Compose do Odoo usa essa base; o runner IDE continua sendo Python local no host. |
| Dependências Python do runner | Python 3.12; entre as versões condicionais: `gevent 24.2.1`, `lxml 6.1.3`, `Pillow 10.2.0`, `psycopg2 2.9.9` e `python-ldap 3.4.4` | `requirements.txt` define as dependências e marcadores de versão; `constraints-voigt.txt` congela as versões selecionadas. Consulte ambos como fonte de verdade, pois nem todas as dependências indiretas precisam estar declaradas diretamente no primeiro arquivo. |
| Dependências nativas da IDE | Pacotes da distribuição correspondente ao codinome e arquitetura atuais | `ide-first-run.sh` simula a resolução APT, baixa os pacotes de desenvolvimento/runtime e monta um prefixo específico do host em `local-infra/.local/native`. Depois da primeira execução atualizada, `current/packages.tsv` registra nome, versão, arquitetura e se cada arquivo foi extraído no prefixo ou mantido como biblioteca base do sistema. Esse diretório não é versionado nem deve ser copiado entre distribuições ou arquiteturas. |

### Conferir o ambiente em outro computador

Execute estes comandos antes de comparar uma falha ou compartilhar um relatório de ambiente:

```bash
cat /etc/os-release
uname -m
git rev-parse --short HEAD
bash --version | head -n 1
apt-get --version | head -n 1
dpkg --version | head -n 1
gcc --version | head -n 1
pkg-config --version
python3.12 --version
if [[ -x .venv/bin/python ]]; then .venv/bin/python --version; fi
docker --version
docker compose version
idea --version
docker image inspect postgres:16-bookworm --format '{{.Id}} {{join .RepoDigests " "}}'
if [[ -f local-infra/.local/native/current/packages.tsv ]]; then
  column -t -s $'\t' local-infra/.local/native/current/packages.tsv
fi
```

Com o PostgreSQL local em execução, consulte também a versão efetiva do servidor:

```bash
docker compose --project-directory local-infra --env-file local-infra/.env \
  -f local-infra/compose.yaml exec -T db postgres --version
```

Depois de preparar o runner, consulte as dependências Python efetivamente instaladas e as bibliotecas nativas resolvidas para esse computador:

```bash
.venv/bin/python -m pip freeze
column -t -s $'\t' local-infra/.local/native/current/packages.tsv
```

`pip freeze` é um retrato do ambiente naquele momento; `requirements.txt` e `constraints-voigt.txt` continuam sendo as fontes versionadas usadas para reconstruí-lo. O inventário nativo registra pacote, versão, arquitetura e escopo (extraído no prefixo local ou fornecido como biblioteca base do sistema). Compartilhe esses resultados junto com a distribuição, arquitetura e revisão Git ao comparar computadores; remova senhas e outros dados locais de qualquer relatório antes de compartilhá-lo.

Para reproduzir a preparação em outro computador, mantenha Python 3.12 disponível no `PATH`, Docker com `docker compose`, e APT/dpkg nos hosts Debian/Ubuntu/Pop!_OS suportados. Execute `ide-first-run.sh` naquele checkout para criar um prefixo nativo adequado ao sistema e à arquitetura locais. Não copie `.venv` nem `local-infra/.local/native` entre computadores: ambos podem conter binários e bibliotecas ligados ao sistema de origem. As configurações da IDE e os requisitos versionados podem ser compartilhados; a instalação dos plugins e os binários da IDE devem ser conferidos no próprio computador.

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

### Guia 1 — configurar o runner pela primeira vez (manual)

Execute este guia uma vez para cada checkout do projeto. Se `requirements.txt` ou `constraints-voigt.txt` mudarem, repita a sincronização Python; o script compara os hashes e evita reinstalar sem necessidade.

1. Crie o arquivo de ambiente local e configure as duas senhas:

   ```bash
   ./local-infra/scripts/setup.sh
   ```

   Edite `local-infra/.env` e substitua `POSTGRES_PASSWORD` e `ODOO_ADMIN_PASSWD`. O arquivo não deve ser versionado.

2. Prepare as bibliotecas de desenvolvimento sem instalá-las no sistema:

   ```bash
   ./local-infra/scripts/ide-first-run.sh --native-deps-only
   ```

   O script baixa pacotes compatíveis com o codinome do host e extrai os arquivos em `local-infra/.local/native`. Requer Docker Compose, APT e `sudo` para atualizar índices/baixar arquivos; não instala nem atualiza bibliotecas globais. A configuração é repetível e protegida por lock.

3. Prepare e sincronize o interpretador virtual e os arquivos locais de credenciais:

   ```bash
   ./local-infra/scripts/setup-ide.sh
   ```

   O script usa o bootstrap para criar `.venv` se necessário e instalar as dependências de `requirements.txt`, respeitando `constraints-voigt.txt`. Cria também `local-infra/.pgpass` e `local-infra/.local/ide-odoo.conf`, ambos com permissão 0600. Esses arquivos contêm credenciais locais e são ignorados pelo Git.

   O runner usa Python 3.12 e as versões de dependências/restrições definidas neste repositório. O bootstrap configura `LD_LIBRARY_PATH`, `LDFLAGS`, `CPATH`, `PKG_CONFIG_PATH` e `PATH` somente nos processos da IDE para usar o prefixo local extraído e priorizar bibliotecas compartilhadas durante a compilação.

4. Abra o repositório no IntelliJ IDEA e confirme que o plugin Python está habilitado. A configuração **Voigt Odoo Local (IDE Debug/Test)** deve aparecer no seletor Run/Debug porque está salva em `.idea/runConfigurations`.
5. Registre a `.venv` como um Python SDK no perfil local do IntelliJ (uma vez por instalação/perfil da IDE): abra **File | Project Structure | Platform Settings | SDKs**, clique em **+ | Add Python SDK from disk**, escolha o ambiente existente e selecione `$PROJECT_DIR$/.venv/bin/python`. Dê ao SDK o nome exato **Python 3.12 (voigt-erp-by-odoo .venv)**; se a IDE já o cadastrou com um nome contendo o caminho local, edite o campo **Name** para usar esse nome estável. O projeto compartilha o nome e o caminho relativo; o registro do SDK e o caminho absoluto ficam no perfil da IDE.
6. O módulo Java do checkout inclui uma facet Python compartilhada em `.idea/voigt-erp-by-odoo.iml`, sem substituir o JDK herdado. Se a IDE estava aberta antes de atualizar o repositório, feche e reabra o projeto para carregar o módulo e a facet.
7. Abra **Run | Edit Configurations** e confirme **Use specified interpreter** com **Python 3.12 (voigt-erp-by-odoo .venv)**. Se aparecer `<No interpreter>`, clique no seletor e escolha o SDK registrado no passo 5. Não aponte para `local-infra/ide-runner/python_interpreter.py`: esse arquivo é um bootstrap usado pelos scripts, não um executável Python nem um SDK da IDE. Mantenha `IS_MODULE_SDK=false` para que a configuração não use o JDK Java do módulo.

### Guia 2 — rotina diária para executar e depurar (manual)

1. Inicie o Docker Desktop/Engine e confirme que `local-infra/.env` continua presente. Execute `./local-infra/scripts/ide-day.sh` para preparar/sincronizar `.venv`, gerar o arquivo local de bibliotecas e iniciar somente o PostgreSQL necessário.
2. Confirme que a aplicação Odoo em Compose está parada. Se o serviço `odoo` estiver em execução, pare somente esse serviço:

   ```bash
   docker compose --project-directory local-infra --env-file local-infra/.env -f local-infra/compose.yaml stop odoo
   ```

3. No seletor de configurações do IntelliJ, escolha **Voigt Odoo Local (IDE Debug/Test)** e clique em **Run** ou **Debug**. O runner atualiza as credenciais e inicia somente o PostgreSQL `db` caso esteja parado; `ide-day.sh` já prepara o ambiente Python e o banco para o fluxo diário.
4. A configuração usa HTTP em `127.0.0.1:8070`, separado da porta 8069 do Odoo em container. Acesse [http://127.0.0.1:8070](http://127.0.0.1:8070). Defina breakpoints no código Python do Odoo ou dos addons e use o painel **Debug** para inspecionar a execução.
5. Ao terminar, use **Stop** na janela Run/Debug. O PostgreSQL continua ativo para manter a conexão do Database Tools. Quando quiser pará-lo também, execute `./local-infra/scripts/stop-ide.sh`.

Se quiser usar o PostgreSQL no Database Tools antes de iniciar a aplicação, execute `./local-infra/scripts/start-ide.sh`. Para Run/Debug, esse passo é opcional porque o runner inicia o banco automaticamente.

### Preparar antes de Run/Debug e proteções do runner

O bootstrap `local-infra/ide-runner/python_interpreter.py`, usado pelos scripts de preparação, cria `.venv` com Python 3.12 se ela não existir e sincroniza dependências quando os requisitos ou o manifesto nativo mudam. A configuração Run/Debug aponta diretamente para `.venv/bin/python`, que precisa estar cadastrado como Python SDK no perfil do IntelliJ. `setup-ide.sh` também gera `.local/ide-runner.env` com os caminhos multiarch das bibliotecas compartilhadas privadas; a configuração importa esse arquivo antes de iniciar Python, permitindo que extensões como `psycopg2` encontrem `libpq.so.5` sem instalar bibliotecas no host. O runner valida a versão Python e confirma que o IntelliJ carregou esse caminho nativo antes de criar marcador PID, atualizar credenciais ou iniciar serviços. Se faltar o ambiente ou a biblioteca, encerra com uma instrução específica sem iniciar Odoo ou Compose:

1. Cria um marcador PID local para impedir que scripts Compose parem ou iniciem serviços durante a depuração.
2. Lê `local-infra/.env` e gera/atualiza `.pgpass` e `ide-odoo.conf` com permissões 0600. A senha não fica na configuração versionada do IntelliJ.
3. Verifica se o Odoo em container está ativo; se estiver, encerra com uma instrução de como alternar os modos.
4. Executa `docker compose up --detach --wait db`: somente o PostgreSQL é criado/iniciado; não sobe o serviço `odoo` da Compose.
5. Confirma a saúde com `pg_isready` e testa a porta TCP publicada.
6. Inicia o `odoo-bin` a partir do código oficial da raiz, com `.venv` e o debugger da IDE.

Se uma etapa falhar, o wrapper encerra e remove o marcador PID. Os scripts `start.sh`, `stop.sh`, `reset.sh`, `start-ide.sh` e `stop-ide.sh` verificam esse marcador para proteger a sessão da IDE.

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
- `setup-ide.sh` sincroniza as dependências Python dentro de `.venv` e prepara credenciais locais com permissões restritas. As bibliotecas nativas baixadas pelo wrapper ficam em `local-infra/.local/native`, fora de `/usr`. A cada execução do runner, `.pgpass` e `ide-odoo.conf` são atualizados para refletir o `.env` local.
- O bootstrap Python e o interpretador `.venv` ficam fora do código Odoo oficial e da imagem Docker. Se `.venv` for removido, o próximo Run/Debug a recria; `setup-ide.sh` também pode prepará-la explicitamente.

### Por que a configuração fica no repositório

O JetBrains permite salvar configurações compartilhadas como arquivos do projeto; o local padrão é `.idea/runConfigurations`. O `.gitignore` deste repositório ignora arquivos privados do IntelliJ, mas abre exceção somente para arquivos XML nessa subpasta. Assim, o runner pode ser distribuído com o projeto sem versionar configurações pessoais, credenciais, histórico da IDE ou fontes de dados locais.

## Solução de problemas

| Sintoma | Causa provável | Efeito | Ação |
| --- | --- | --- | --- |
| `apt-get` informa `Unable to locate package ...` | O nome do pacote não existe nessa versão; nomes de bibliotecas de desenvolvimento podem mudar entre Debian/Ubuntu e derivados. | Nenhum pacote do sistema é instalado; a preparação local é interrompida. | Execute novamente `./local-infra/scripts/ide-first-run.sh`: ele busca alternativas conhecidas e baixa/extrai apenas a solução compatível. |
| Simulação ou download APT falha por dependências ou suite incompatível | As fontes APT misturam versões diferentes do sistema. Neste host Pop!_OS 24.04/Noble, por exemplo, há índice Jammy que oferece `libfreetype6-dev` exigindo uma versão Jammy incompatível com Noble. | A preparação para antes de mudar o prefixo ativo; nenhum pacote é instalado no sistema. | Examine as fontes com `grep -RniE 'jammy|noble' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null` e `apt-cache policy libfreetype6-dev libfreetype-dev`. Corrija/desative entradas de outra versão conforme a origem, execute `sudo apt-get update` e tente novamente. Não faça um upgrade geral do sistema como atalho. |
| Runner informa que Docker não pode ser consultado | Docker Desktop/Engine está parado ou o usuário não tem acesso ao daemon. | O PostgreSQL não inicia e o Odoo IDE não é executado. | Inicie o Docker e confirme `docker info`; depois use Run/Debug novamente. |
| `ide-first-run.sh` cria `.env` e encerra | É a primeira execução e o template ainda contém credenciais de exemplo. | A preparação e os serviços não iniciam até que as senhas sejam definidas. | Preencha `POSTGRES_PASSWORD` e `ODOO_ADMIN_PASSWD` em `local-infra/.env` e execute o script novamente. |
| `ide-first-run.sh` não consegue baixar pacotes com `sudo` | O host não permite autenticação administrativa ou não usa APT/dpkg. | O prefixo nativo local não é criado e extensões Python que exigem compilação podem falhar. | Execute em terminal interativo com autorização para atualizar índices e baixar arquivos; em outra distribuição, prepare o prefixo nativo equivalente sem instalar bibliotecas globais. |
| `setup-ide.sh` para em `pg_config` ou dependências nativas | O prefixo local não foi preparado ou o bootstrap não o carregou. | O `.venv` não recebe todas as dependências do Odoo. | Execute `./local-infra/scripts/ide-first-run.sh --native-deps-only` e depois `./local-infra/scripts/setup-ide.sh`; confirme que `.venv/bin/python` existe e que a configuração IntelliJ aponta para ele. |
| Compilação de `python-ldap` falha com `relocation ... can not be used when making a shared object; recompile with -fPIC` | O prefixo continha o arquivo de desenvolvimento `libldap.a`, mas não a biblioteca de runtime que satisfaz o link simbólico `libldap.so`. O bootstrap também colocava o prefixo em `LIBRARY_PATH`, então o linker escolheu o arquivo estático sem PIC para construir `_ldap` como extensão compartilhada. | A compilação dos requisitos falha e o runner não inicia. | Execute novamente `./local-infra/scripts/ide-first-run.sh`: o conjunto local agora inclui bibliotecas de runtime (como `libldap2`), não coloca o prefixo em `LIBRARY_PATH`, passa `LDFLAGS` com caminhos locais, remove arquivos `.a` e troca o prefixo atomicamente. A mudança do manifesto invalida o hash de dependências e repete a sincronização da `.venv`. |
| APT avisa que o download foi feito sem sandbox como `root` | A pasta temporária de arquivos `.deb` não permite travessia pelo usuário `_apt`. | O download pode terminar, mas o sandbox de aquisição do APT não foi usado. | O wrapper atual grava arquivos temporários em `/tmp` com permissões de travessia e remove a pasta ao encerrar; execute a versão atual do script. |
| IntelliJ mostra `<No interpreter>` ou `Please select a valid Python interpreter` | O plugin Python está ativo, mas nenhum Python SDK local foi registrado, ou o nome do SDK não corresponde ao `SDK_NAME` compartilhado. O caminho em `SDK_HOME` não registra sozinho um SDK no perfil da IDE. | Run/Debug é bloqueado antes de executar o runner; Docker e Odoo não são iniciados. | Rode `./local-infra/scripts/ide-day.sh`; em **File | Project Structure | Platform Settings | SDKs**, adicione como Python SDK existente `$PROJECT_DIR$/.venv/bin/python` e nomeie-o `Python 3.12 (voigt-erp-by-odoo .venv)`. Reabra o projeto e selecione esse SDK na configuração. |
| Runner mostra `ImportError: libpq.so.5: cannot open shared object file` | O `LD_LIBRARY_PATH` do processo não inclui o diretório multiarch privado que contém `libpq.so.5`. Isso ocorre quando o `ENV_FILES` da configuração não carregou `local-infra/.local/ide-runner.env`, por exemplo porque a IDE manteve uma configuração em cache. | `psycopg2` não encontra a biblioteca dinâmica e o Odoo encerra ao importar o driver. | Execute `./local-infra/scripts/ide-day.sh`, confira se `.local/ide-runner.env` contém o diretório de `libpq.so.5`, confirme `ENV_FILES=$PROJECT_DIR$/local-infra/.local/ide-runner.env` no XML e recarregue a configuração no IntelliJ. O runner agora verifica esse pré-requisito antes de criar o marcador PID ou iniciar serviços e apresenta uma mensagem direta se o ambiente não for carregado. |
| A configuração mostra `[Invalid] Python 3.10` ou executa Python de outro projeto | A IDE manteve uma associação local de SDK antiga ou selecionou um SDK registrado sob nome incorreto. | O processo inicia com Python incorreto ou a IDE rejeita a configuração. | Execute `./local-infra/scripts/ide-day.sh`, recarregue `.idea/runConfigurations/Voigt_Odoo_IDE.xml` e escolha **Python 3.12 (voigt-erp-by-odoo .venv)**, registrado a partir de `.venv/bin/python`. Confirme `SDK_HOME=$PROJECT_DIR$/.venv/bin/python` e `IS_MODULE_SDK=false`. |
| O bootstrap informa que Python 3.12 não foi encontrado ou `.venv` usa versão antiga | Python 3.12/`venv` não está disponível no `PATH`, ou o ambiente virtual foi criado anteriormente com Python abaixo de 3.12. | A preparação para antes de iniciar Odoo e PostgreSQL. | Disponibilize Python 3.12 por um método aprovado para o host (o wrapper não instala nem atualiza Python global). Mova/remova a `.venv` antiga e execute `./local-infra/scripts/ide-first-run.sh` novamente. |
| `.venv` não existe | A configuração Run/Debug aponta para o executável local antes de a preparação tê-lo criado. | A IDE não consegue iniciar o runner. | Execute `./local-infra/scripts/ide-day.sh`, que prepara/sincroniza `.venv` e inicia somente o PostgreSQL. |
| Runner diz que faltam `POSTGRES_PASSWORD` ou `ODOO_ADMIN_PASSWD` | `.env` não existe ou ainda tem valores de exemplo. | Credenciais não são materializadas; o processo para antes de subir o banco. | Execute `setup.sh`, preencha `local-infra/.env` e tente de novo. |
| Runner informa que Odoo Compose está ativo | O container `odoo` ainda está rodando. | O wrapper interrompe a inicialização para evitar dois servidores usando o mesmo banco. | Pare a configuração IDE e então use `docker compose ... stop odoo` antes de rodar a IDE; ou pare o runner e use `start.sh` para Compose. |
| PostgreSQL não fica saudável durante Run/Debug | Inicialização do container falhou, volume está inconsistente ou a porta do host está ocupada. | O wrapper não chama `odoo-bin`. | Consulte `./local-infra/scripts/logs.sh db`, verifique `./local-infra/scripts/db-ide.sh status` e escolha outra `DB_IDE_PORT` se houver conflito. |
| Erro de conexão TCP para `127.0.0.1:15432` | A porta foi alterada, está ocupada pelo túnel cloud ou não foi publicada. | O `pg_isready` interno pode passar, mas o host/IDE não acessa o banco. | Confira `.env`, pare o túnel cloud se usar a mesma porta, ajuste `PGPORT` na configuração IntelliJ e execute novamente. |
| O IDE informa senha PostgreSQL inválida | `.env` mudou após a criação do volume, ou a senha no volume é antiga. | O Odoo e o Database Tools não autenticam. | Para dados descartáveis, use `reset.sh`; para preservar dados, altere a senha da role PostgreSQL para o valor do `.env`. |
| Script diz que outro runner está ativo ou `stop-ide.sh` recusa parar | A configuração Python ainda está rodando ou sobrou um PID obsoleto. | Scripts de infraestrutura se recusam a desligar o banco durante depuração. | Pare o processo pelo botão Stop. Se ele já encerrou, confira `.local/ide-runner.pid`; remova somente se o PID não existir. |
| Odoo inicia mas não encontra anexos antigos | Runner e container usam diretórios de filestore diferentes. | Registros do banco aparecem, mas os arquivos armazenados podem faltar. | Use o modo container para fluxos com anexos existentes ou copie o filestore deliberadamente antes de depurar. |
| Configuração não aparece no IntelliJ | Arquivo XML não foi carregado ou plugin Python está desabilitado. | A configuração não aparece no seletor Run/Debug. | Confirme `.idea/runConfigurations/Voigt_Odoo_IDE.xml`, habilite Python e reabra o projeto. |
| Runner mostra `Outdated python version` ou informa que a IDE selecionou Python abaixo de 3.12 | A configuração local da IDE continuou associando o nome antigo `Python 3.10 (venv)` a um ambiente de outro projeto; o processo usou esse executável em vez da `.venv` local. | O Odoo encerra na validação de `odoo/init.py`; versões antigas também podem falhar antes de carregar dependências. | Execute `./local-infra/scripts/ide-day.sh`; edite a configuração compartilhada para usar `$PROJECT_DIR$/.venv/bin/python` (ou recarregue-a do disco) e mantenha **Use specified interpreter** / `IS_MODULE_SDK=false`. Confirme com `.venv/bin/python --version` que informa Python 3.12 ou superior. |
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
| `scripts/setup-ide.sh` | Com o runner parado, sincroniza o virtualenv Python e materializa credenciais somente locais com permissões restritivas para o IntelliJ, evitando trocar dependências enquanto o processo está depurando. |
| `scripts/ide-first-run.sh` | Wrapper idempotente do primeiro guia. Cria/valida `.env`, identifica a versão do sistema, valida alternativas e baixa pacotes `.deb` sem instalá-los. Extrai dependências de desenvolvimento e runtime, inclusive dependências transitivas, em um prefixo versionado dentro de `.local`; remove arquivos estáticos `.a` para as extensões compartilhadas e ativa o conjunto por troca atômica de symlink, sem substituir bibliotecas globais. |
| `scripts/ide-day.sh` | Wrapper idempotente do guia diário. Garante a preparação local, para apenas o Odoo em Compose quando necessário e inicia somente o PostgreSQL antes do usuário executar Run/Debug no IntelliJ. |
| `ide-runner/odoo_ide_runner.py` | Código auxiliar isolado fora das pastas oficiais da plataforma. Valida Python e `LD_LIBRARY_PATH`/`libpq.so.5` antes de criar arquivos ou iniciar serviços, cria credenciais locais, verifica Compose, mantém marcador PID, sobe somente o PostgreSQL se necessário e delega ao `odoo-bin` oficial no processo depurável da IDE. |
| `ide-runner/prepare_ide_files.py` | Compartilha a leitura do `.env` e a criação atômica dos arquivos `.pgpass` e `ide-odoo.conf` entre a preparação inicial e cada execução, mantendo permissões restritivas sem duplicar lógica. |
| `ide-runner/python_interpreter.py` | Bootstrap usado pelos scripts de preparação para criar `.venv` e sincronizar dependências de modo idempotente quando os requisitos ou o manifesto nativo mudam. Fica fora do código oficial do Odoo; a configuração Run/Debug usa o executável real `.venv/bin/python`, reconhecido pelo IntelliJ. |
| `local-infra/.local/ide-runner.env` | Arquivo gerado localmente por `setup-ide.sh` com os diretórios multiarch de bibliotecas privadas. A configuração Python o carrega para permitir importação de extensões nativas sem modificar variáveis globais nem instalar bibliotecas do sistema. É ignorado pelo Git e refeito idempotentemente a cada preparação. |
| `local-infra/.local/native/current` | Link para o conjunto versionado de bibliotecas nativas de desenvolvimento e runtime extraídas localmente. O bootstrap injeta `LD_LIBRARY_PATH`, `LDFLAGS`, include paths, `pkg-config` e ferramentas apenas nos processos Python da IDE; os pacotes não são registrados pelo dpkg nem colocados em `/usr`. |
| `local-infra/.local/native/current/packages.tsv` | Inventário específico do host com nome, versão Debian, arquitetura e escopo dos pacotes nativos considerados na preparação. Permite comparar resoluções entre distribuições sem supor que nomes ou versões APT sejam iguais; é gerado junto com o prefixo local e não deve ser versionado nem copiado para outro sistema. |
| `.idea/runConfigurations/Voigt_Odoo_IDE.xml` | Configuração compartilhada Python do IntelliJ, com interpretador do projeto, caminho do runner, conexão PostgreSQL local e porta HTTP alternativa. Não contém senhas. |
| `.idea/modules.xml` e `.idea/voigt-erp-by-odoo.iml` | Registram o módulo do projeto e sua facet Python para que o plugin reconheça o código Odoo dentro do módulo Java existente. A facet usa um nome estável de SDK e preserva o JDK herdado, sem caminhos absolutos do computador. |
| `.gitignore` (raiz) | Mantém arquivos pessoais do IntelliJ ignorados, liberando somente as configurações Run/Debug compartilhadas, o registro básico do módulo e sua facet Python. O SDK efetivo continua no perfil local da IDE. |
| `.dockerignore` | Exclui toda a infraestrutura local, a configuração IntelliJ e o virtualenv do contexto enviado ao Docker, evitando incorporar artefatos de desenvolvimento à imagem Odoo. |
| `local-infra/.gitignore` | Exclui credenciais PostgreSQL, configuração gerada do runner e dados locais do filestore. |
| `README.md` | Explica a configuração inicial, o uso diário, a arquitetura, a configuração, a persistência, a recuperação e a justificativa de cada artefato gerado. |

## Referências externas utilizadas

- Ordem de inicialização no Docker Compose: o Compose aguarda a verificação de saúde de uma dependência quando `depends_on` usa a condição `service_healthy`. [Documentação do Docker](https://docs.docker.com/compose/how-tos/startup-order)
- Definições de serviços e volumes do Docker Compose: [referência de serviços do Compose](https://docs.docker.com/reference/compose-file/services/) e [guia de início rápido do Compose](https://docs.docker.com/compose/gettingstarted/).
- O Odoo requer PostgreSQL e deve se conectar usando um usuário dedicado, em vez do superusuário do PostgreSQL. [Documentação de instalação do Odoo](https://www.odoo.com/documentation/saas-15.4/administration/install/install.html).
- Configurações de execução compartilhadas do IntelliJ podem ser armazenadas como arquivos do projeto; o padrão é `.idea/runConfigurations`. [Documentação de Run/Debug Configurations do IntelliJ IDEA](https://www.jetbrains.com/help/idea/run-debug-configuration.html).
- A versão do Docker Compose pode ser consultada por `docker compose version`; esse comando é fornecido pelo plugin Compose instalado no host. [Referência oficial da CLI Docker Compose](https://docs.docker.com/reference/cli/docker/compose/version/).
- O suporte a Python na IntelliJ depende do plugin Python habilitado, que fornece SDKs e configurações Python de Run/Debug. [Documentação de Python na IntelliJ IDEA](https://www.jetbrains.com/help/idea/python.html).
- O IntelliJ exige que um Python SDK seja cadastrado no perfil da IDE e recomenda uma facet Python ao trabalhar com Python em módulo de outro tipo. [Configurar Python SDK na IntelliJ IDEA](https://www.jetbrains.com/help/idea/configuring-python-sdk.html) e [configurar a facet Python em um módulo existente](https://support.jetbrains.com/hc/en-us/articles/40249576578322-How-to-configure-Python-Facet-Configuration-in-the-iml-file-in-IntelliJ-IDEA).
- As configurações Run/Debug do IntelliJ podem carregar variáveis de ambiente a partir de arquivos; o runner usa esse recurso para injetar o caminho das bibliotecas nativas somente no processo iniciado pela IDE. [Variáveis de ambiente e arquivos `.env` no IntelliJ IDEA](https://www.jetbrains.com/help/idea/program-arguments-and-environment-variables.html).
- O APT usa prioridades para selecionar versões candidatas; o wrapper direciona a resolução para o codinome do host, simula o download e extrai os arquivos em um prefixo do projeto sem instalação global, seguindo o comportamento documentado de preferências do APT. [Manual `apt_preferences` para Ubuntu Noble](https://manpages.ubuntu.com/manpages/noble/man5/apt_preferences.5.html). Fontes de terceiros devem ser configuradas para a versão correta do sistema. [Gerenciar fontes de software no Ubuntu](https://help.ubuntu.com/stable/ubuntu-help/addremove-sources.html).
- O GCC consulta `LIBRARY_PATH` ao buscar bibliotecas `-l`; o bootstrap evita acrescentar o prefixo local a essa variável, passa `LDFLAGS` com os diretórios locais compartilhados e remove arquivos `.a` para que uma extensão compartilhada não selecione acidentalmente uma biblioteca estática. [Variáveis de ambiente do GCC](https://gcc.gnu.org/onlinedocs/gcc/Environment-Variables.html) e [opções de link do GCC](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html).
- O IntelliJ guarda `SDK_NAME` e `SDK_HOME` na configuração Python compartilhada; se um nome antigo corresponder a um SDK já registrado, a IDE pode usá-lo em vez do caminho do projeto. A configuração usa um nome próprio e aponta para `.venv/bin/python`, preparada pelos scripts locais. [Compartilhamento de configurações do PyCharm](https://www.jetbrains.com/help/pycharm/sharing-project-settings.html) e [configurar Python SDK na IntelliJ IDEA](https://www.jetbrains.com/help/idea/configuring-python-sdk.html).
- O JetBrains oferece intérpretes Python locais e remotos via Docker/Compose; este runner escolhe um interpretador local para permitir depuração Python direta do processo. [Configurar um interpretador Python](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html).
- O plugin oficial OdooLS para PyCharm fornece recursos do servidor de linguagem, incluindo informações contextuais, navegação, autocompletar e diagnósticos. [Repositório oficial Odoo para o plugin](https://github.com/odoo/odoo-pycharm) e [guia de uso do OdooLS](https://github.com/odoo/odoo-ls/wiki/2.-How-to-use).

A página de instalação do Odoo é antiga e específica de uma versão anterior. O requisito do PostgreSQL e a recomendação de usar um usuário dedicado continuam aplicáveis; o comportamento em tempo de execução descrito aqui foi baseado no Dockerfile e no entrypoint deste repositório.
