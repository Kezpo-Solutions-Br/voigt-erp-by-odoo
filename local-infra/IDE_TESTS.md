# Runner de testes da plataforma Odoo pelo IntelliJ

Este documento descreve a configuração **Voigt Odoo Local (Testes da Plataforma)**, os artefatos que a compõem e como preparar e executar a suíte oficial de testes do checkout local. O runner executa o `odoo-bin` e os módulos presentes neste repositório; não usa a imagem Odoo do Compose para executar os testes.

## Escopo dos testes

O runner inicializa a base usando o comando oficial `odoo-bin db init --force --with-demo`, que cria extensões e estruturas esperadas pelo Odoo e carrega dados de demonstração. Em seguida usa `--init=all`, `--update=all`, `--test-tags=+standard` e `--stop-after-init`: instala os módulos disponíveis, atualiza a base inicial para incluir seus testes e encerra depois da carga/testes, sem manter o servidor de desenvolvimento ligado. O Odoo 20.0 documenta três categorias de teste — Python, JavaScript e tours — e que `--test-tags` habilita e seleciona testes pelos marcadores; `standard` é o conjunto padrão de classes derivadas de `BaseCase`.

O rótulo `standard` é o escopo de teste mantido pelo próprio Odoo. Ele pode incluir testes transacionais, testes HTTP e outras classes derivadas de `BaseCase`; portanto, não significa que cada caso seja um teste unitário puro sem integração. Esta configuração executa os testes Python selecionados pelo Odoo, mas não inicia separadamente a suíte JavaScript do navegador. Testes que não estejam selecionados por `standard`, testes customizados de addons fora dos caminhos padrão e testes que dependam de serviços externos não são prometidos por esta configuração.

Referências oficiais consultadas:

- [Testes do Odoo 20.0](https://www.odoo.com/documentation/20.0/developer/reference/backend/testing.html)
- [CLI do Odoo 20.0: opções de teste](https://www.odoo.com/documentation/20.0/developer/reference/cli.html)
- [Configurações Run/Debug compartilhadas no IntelliJ IDEA](https://www.jetbrains.com/help/idea/run-debug-configuration.html)

## Artefatos gerados e decisões

| Artefato | Responsabilidade | Justificativa |
| --- | --- | --- |
| `.idea/runConfigurations/Voigt_Odoo_IDE_Tests.xml` | Runner Python compartilhado, salvo junto à configuração existente da aplicação. Usa `$PROJECT_DIR$/.venv/bin/python`, o diretório raiz do projeto, as variáveis locais e o arquivo `odoo_ide_test_runner.py`. | O IntelliJ armazena configurações compartilháveis como XML em `.idea/runConfigurations`. Manter um arquivo separado deixa a execução de testes selecionável independentemente do servidor Odoo e permite versioná-la com o projeto. |
| `local-infra/ide-runner/odoo_ide_test_runner.py` | Valida Python e bibliotecas nativas, sincroniza dependências, garante PostgreSQL local, protege a execução concorrente, recria o banco temporário com `odoo-bin db init`, inicia os testes Odoo e remove banco/filestore ao final. | O código de apoio fica isolado do código oficial em `odoo/`, `addons/` e `odoo-bin`. `runpy` executa o comando de testes no mesmo processo iniciado pelo IntelliJ, mantendo breakpoints disponíveis. |
| `local-infra/scripts/ide-test-first-run.sh` | Prepara as credenciais locais automaticamente quando estão ausentes ou ainda são placeholders, executa o bootstrap completo e deixa o PostgreSQL pronto para testes. | Evita exigir edição manual de senhas no primeiro checkout. Gera segredos fortes sem imprimi-los, preserva valores locais válidos e recusa gerar uma nova senha PostgreSQL quando já existe um volume persistente sem credencial conhecida. |
| `local-infra/scripts/ide-test-day.sh` | Prepara dependências locais, impede conflito com outro runner, para apenas o serviço Odoo em Compose e inicia apenas o PostgreSQL. | Fornece um comando repetível para deixar a infraestrutura no modo de testes. Reutiliza os scripts existentes de dependências e banco em vez de duplicar sua implementação. |
| `local-infra/IDE_TESTS.md` | Este relatório, com decisões, instruções de primeiro uso, rotina diária e solução de problemas. | Mantém o procedimento junto aos artefatos que administra e em português BR. |
| `local-infra/.local/ide-tests.conf`, `local-infra/data/ide-tests/` | Configuração e diretório de dados/filestore privados criados localmente pelo runner. | Separam arquivos de sessão de teste dos dados do servidor Odoo iniciado pela IDE e dos volumes do Odoo em container; são ignorados pelo Git. |
| `local-infra/.pgpass` | Arquivo de senha usado na conexão local ao PostgreSQL. | Evita gravar a senha no XML versionado; é compartilhado apenas no host e protegido com permissão 0600. |

### Isolamento e segurança operacional

- O runner usa o mesmo serviço PostgreSQL do Compose e a porta local definida por `DB_IDE_PORT`, mas cria e remove somente o banco reservado `voigt_ide_tests`.
- O banco `voigt_ide_tests` é descartado e recriado em cada execução. Não armazene dados de uso manual nesse banco.
- O runner utiliza `local-infra/data/ide-tests` como `data_dir`, separado de `local-infra/data/ide-runner` e do volume `odoo-data` do Compose. Os anexos/filestore de um modo não são compartilhados com os outros.
- Um marcador PID comum impede testes, runner Odoo da IDE e operações dos scripts Compose de interferirem entre si. O runner recusa iniciar enquanto o serviço `odoo` em container estiver ativo.
- O runner de testes e o runner de aplicação são usados em momentos separados. O PostgreSQL pode permanecer ligado para o Database Tools.
- O runner não consulta nem altera credenciais, túneis ou configurações cloud. O XML de teste não configura credenciais AWS.
- Os dois runners IntelliJ usam exatamente a mesma `.venv` existente em `$PROJECT_DIR$/.venv`; não há uma segunda virtualenv nem um conjunto Python separado para testes. O XML da configuração Odoo que já funciona permanece inalterado. O runner de testes valida que o IntelliJ selecionou esse executável e falha com orientação se outro Python for escolhido.
- O bootstrap compartilhado verifica o hash de `requirements.txt`, `constraints-voigt.txt` e do manifesto nativo. Quando nada mudou, reutiliza a `.venv` sem reinstalar pacotes; quando essas entradas mudam, sincroniza o mesmo ambiente conforme o contrato já usado pelo runner Odoo.
- O preparo nativo também disponibiliza `wkhtmltopdf`, as fontes usadas nos PDFs e Cairo no prefixo privado `local-infra/.local/native`. O runner acrescenta os binários privados ao `PATH`, sem instalar pacotes no sistema.
- A `.venv` compartilhada recebe `reportlab[pycairo]==4.1.0` sob demanda pelo runner de testes. ReportLab 4.1 não inclui por padrão o backend de renderização de bitmap usado pelo teste de código de barras; essa extensão não altera os requisitos do servidor Odoo em container.
- Quando o `pip` compila PyCairo, o runner passa os diretórios privados de `pkg-config`, headers e bibliotecas ao processo de build. O bootstrap Python roda em processo filho, então suas variáveis locais não são presumidas no processo pai do runner.
- O runner gera uma configuração Fontconfig privada que inclui as fontes extraídas localmente e a configuração de fontes do host, para que o `wkhtmltopdf` encontre as famílias sem registrá-las globalmente.
- A criação do prefixo de bibliotecas nativas continua isolada em `local-infra/.local/native`; o preparo não instala pacotes APT globalmente. A sincronização Python ocorre somente em `.venv`.
- Uma interrupção forçada do processo pode impedir o bloco de limpeza e deixar o banco de teste reservado no PostgreSQL. A execução seguinte o remove e recria antes de testar; `local-infra/data/ide-tests` é removido pelo runner ao concluir normalmente.

## Guia 1 — primeira configuração automatizada

Execute uma vez por checkout. O wrapper também pode ser repetido com segurança: ele mantém credenciais já configuradas, reutiliza dependências locais e sincroniza o ambiente Python apenas quando as entradas mudam.

1. Inicie o Docker Engine/Desktop e, na raiz do repositório, execute:

   ```bash
   ./local-infra/scripts/ide-test-first-run.sh
   ```

   O wrapper cria `local-infra/.env` quando necessário e gera senhas aleatórias fortes para `POSTGRES_PASSWORD` e `ODOO_ADMIN_PASSWD` sem mostrá-las na tela. Mantém as credenciais válidas existentes, protege o arquivo com permissão 0600 e prepara dependências nativas isoladas, a `.venv` já compartilhada com o runner da aplicação, os arquivos privados e o PostgreSQL. Ele não cria uma virtualenv de testes nem troca a configuração existente do runner Odoo. As senhas podem ser consultadas localmente em `local-infra/.env` quando necessário. O arquivo não é versionado.

   Se o wrapper detectar um volume PostgreSQL existente sem uma senha conhecida, ele para sem substituir a credencial. Restaure a cópia correta de `local-infra/.env` para preservar esse banco. Não altere a senha de um volume existente gerando uma nova credencial.

   A preparação nativa pode pedir a senha do `sudo` para atualizar índices e baixar pacotes compatíveis com o sistema. Os pacotes são extraídos no prefixo local do projeto; não são instalados globalmente. Python 3.12 precisa estar disponível no host: o script não substitui nem atualiza um Python global.

   Se um volume PostgreSQL já existir sem um `local-infra/.env` válido, o wrapper para antes de iniciar os testes. Recupere a senha original do arquivo de ambiente/backup; uma senha aleatória nova não autentica no volume existente. Não apague o volume para contornar essa validação.

2. Abra a raiz do repositório no IntelliJ IDEA e confirme que o plugin Python está habilitado. A configuração compartilhada **Voigt Odoo Local (Testes da Plataforma)** deve aparecer no seletor Run/Debug.
3. Se a IDE indicar interpretador inválido, edite a configuração uma vez e selecione `Use specified interpreter` apontando para `$PROJECT_DIR$/.venv/bin/python`. O caminho já está gravado no XML; normalmente basta associá-lo ao SDK local do IntelliJ.

## Guia 2 — rotina diária

1. Inicie o Docker Engine/Desktop e, na raiz do projeto, execute:

   ```bash
   ./local-infra/scripts/ide-test-day.sh
   ```

   O script é idempotente: verifica e prepara dependências, mantém somente o serviço PostgreSQL ativo e para o serviço Odoo em Compose se necessário. Ele falha se um runner Odoo da IDE ainda estiver ativo. Não é necessário executar `ide-first-run.sh`, `setup-ide.sh` ou `start-ide.sh` manualmente.

2. No IntelliJ, selecione **Voigt Odoo Local (Testes da Plataforma)** e clique em **Run**. Para depurar os testes, clique em **Debug**; coloque breakpoints nos testes ou no código oficial do Odoo.
3. Acompanhe a saída no painel Run/Debug. O processo cria uma base limpa, instala todos os módulos disponíveis no ambiente Odoo, executa os testes `standard` e termina após a inicialização/testes. O banco temporário e seu filestore são removidos ao fim.
4. O serviço PostgreSQL permanece ativo para o JetBrains Database Tools. Para pará-lo depois de confirmar que nenhum runner IDE/Compose está ativo, execute:

   ```bash
   ./local-infra/scripts/stop-ide.sh
   ```

5. Para voltar ao Odoo em container, pare a sessão de testes na IDE e execute `./local-infra/scripts/start.sh`. Para retornar aos testes, execute `ide-test-day.sh` novamente.

O runner IntelliJ sincroniza dependências Python, prepara a configuração privada, verifica o ambiente e inicia o PostgreSQL se estiver parado. O wrapper diário também alterna com segurança o serviço Odoo de Compose, evitando que o usuário precise lembrar a ordem manual dos serviços.

## Execução manual equivalente

O caminho recomendado é executar `./local-infra/scripts/ide-test-first-run.sh` uma vez por checkout, usar `./local-infra/scripts/ide-test-day.sh` no começo do dia e então clicar **Run** ou **Debug** na configuração IntelliJ. O wrapper prepara os serviços; a execução é feita pelo `odoo_ide_test_runner.py`. Não execute diretamente `odoo-bin --test-enable` contra o banco normal do Odoo: isso mistura os efeitos dos testes com dados que não foram criados para esse fim.

## Diagnóstico de problemas

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| Configuração não aparece no IntelliJ | XML ainda não foi recarregado pelo IDE, ou `.idea/runConfigurations` não está versionado/visível. | Reabra o projeto ou use **Run > Edit Configurations** e confirme o arquivo `Voigt_Odoo_IDE_Tests.xml`. |
| `Please select a valid Python interpreter` | O SDK selecionado não existe neste checkout ou está associado a outro ambiente. | Execute `ide-test-first-run.sh`, depois selecione `$PROJECT_DIR$/.venv/bin/python`, o mesmo interpretador configurado no runner Odoo. |
| O runner de testes informa que outro interpretador foi selecionado | A configuração de testes está usando um Python diferente do runner Odoo já funcional. | Edite somente a configuração de testes e selecione `$PROJECT_DIR$/.venv/bin/python`; não crie nem selecione uma segunda `.venv`. |
| Runner informa Python abaixo de 3.12 | A configuração iniciou com Python global antigo. | Troque o interpretador para `.venv/bin/python`; Odoo deste checkout requer Python 3.12 ou superior. |
| `libpq.so.5` ausente ou `LD_LIBRARY_PATH` não carregado | Bibliotecas privadas não foram preparadas ou o IntelliJ não leu o arquivo `ENV_FILES`. | Execute `ide-first-run.sh` e `ide-test-day.sh`; confirme `ENV_FILES` apontando para `$PROJECT_DIR$/local-infra/.local/ide-runner.env` e recarregue a configuração. |
| Testes de relatório dizem `Unable to find the pdf engine` | O runner local não encontrava `wkhtmltopdf`, embora a imagem Docker do Odoo já o instale. | Execute `./local-infra/scripts/ide-test-day.sh` para extrair o binário e as fontes no prefixo privado; não é necessário mudar a imagem nem instalar no sistema. |
| `test_render_barcode` falha ao carregar `renderPM`/`rlPyCairo` | O pacote base ReportLab 4.1 não instala o backend Cairo opcional usado para renderizar imagens de código de barras. | Execute novamente o runner de testes; ele instala `reportlab[pycairo]==4.1.0` na `.venv` compartilhada e usa Cairo do prefixo nativo privado. |
| `test_report_error_cleanup` falha junto com erros de PDF | O teste espera que a geração do relatório alcance a etapa de limpeza; sem `wkhtmltopdf`, ela falha antes dessa etapa. | Corrija a disponibilidade do mecanismo PDF conforme acima e rode a suíte novamente. |
| Preparação informa `Dependency "cairo" not found` ao instalar PyCairo | O backend precisa compilar a extensão, mas o processo do `pip` não recebeu o caminho privado do arquivo `cairo.pc` ou o pacote `libcairo2-dev` não está no prefixo. | Execute `./local-infra/scripts/ide-test-day.sh` para atualizar o prefixo e rode novamente. O runner passa `PKG_CONFIG_PATH`, headers e bibliotecas locais ao build; não instale `libcairo2-dev` globalmente. |
| Erro termina em `AttributeError: 'NoneType' object has no attribute 'strip'` durante preparação | Um erro de dependência do subprocesso não capturava `stderr`, e o tratamento tentava lê-lo como texto, ocultando o erro inicial. | A versão corrigida exibe a saída do `pip` e a orientação para conferir Cairo/`pkg-config`. Resolva o erro inicial mostrado antes do traceback. |
| Docker indisponível ou PostgreSQL não saudável | Engine parado, credenciais inválidas, porta ocupada ou falha de inicialização. | Inicie Docker, confira `local-infra/.env`, execute `./local-infra/scripts/status.sh` e consulte `./local-infra/scripts/logs.sh db`. |
| Primeiro uso informa volume existente sem `POSTGRES_PASSWORD` válido | O arquivo de ambiente foi apagado ou ainda contém valor de exemplo, embora haja dados PostgreSQL persistidos. | Restaure a credencial original de `local-infra/.env` a partir de uma cópia segura. O wrapper não inventa outra senha nem remove o volume. |
| Test runner recusa iniciar por Odoo Compose ativo | Os dois processos disputariam o mesmo PostgreSQL. | Pare o serviço com `./local-infra/scripts/stop.sh` ou execute `ide-test-day.sh`, que para somente o Odoo em Compose. |
| Mensagem de outro runner ativo | A aplicação Odoo da IDE ou outra execução de testes ainda está ativa. | Pare-a na janela Run/Debug antes de iniciar outra configuração. Se o processo terminou abruptamente, verifique o PID em `local-infra/.local/ide-runner.pid`; os scripts removem marcadores obsoletos quando podem confirmar que o PID não existe. |
| Falha durante instalação de módulo/teste | Dependência externa do teste ausente, falha real de teste ou incompatibilidade da árvore atual. | Leia o primeiro traceback e o resumo de falhas no painel Run; instale/configure apenas o serviço explicitamente exigido pelo teste ou corrija o código e rode novamente. O banco é recriado em cada execução. |
| Runner termina, mas aparece aviso ao remover banco | PostgreSQL foi parado ou ficou indisponível durante a limpeza. | Inicie o banco e rode novamente; o próximo ciclo descarta e recria `voigt_ide_tests`. Não remova outros bancos. |

## Análise da execução reportada

A saída fornecida mostra que o PostgreSQL conectou, o banco temporário foi criado, os módulos carregaram e o runner executou 1.041 testes. Portanto, a falha não ocorreu na configuração da base ou na inicialização do Odoo. O resumo final aponta seis erros de relatório/PDF e uma falha em `test_report_error_cleanup`:

- Os erros de `test_report_icon_is_a_glyph`, relatórios agregados e recarga de anexos dizem explicitamente `Unable to find the pdf engine`. O processo local não tinha `wkhtmltopdf` no `PATH`. O `Dockerfile` já declara esse binário e as quatro famílias de fontes, mas o prefixo nativo do host não as preparava.
- `test_render_barcode` falha ao renderizar um template QWeb. O requisito base fixa ReportLab 4.1.0, mas a extensão opcional de renderização bitmap não é instalada em Linux pelo arquivo de requisitos; o próprio comentário do requisito diz que ela viria do pacote Debian. A execução local usa a `.venv`, não os pacotes Python do container, então esse backend estava ausente.
- `test_report_error_cleanup` é consequência do primeiro problema: sem motor PDF, o fluxo não chega à chamada de exportação que o teste espera verificar.
- As mensagens sobre `websocket-client`, `aiosmtpd` e outros módulos ausentes indicam testes ignorados opcionais; elas não explicam os sete resultados do resumo final.

As correções locais preparam binário, fontes e Cairo em `local-infra/.local/native`, colocam os executáveis privados no caminho do runner e instalam o extra Cairo do ReportLab na `.venv` somente quando ainda falta. A execução mais recente falhou antes de iniciar o Odoo: `pycairo` tentou compilar, mas `pkg-config` não encontrou `cairo`. O processo principal do runner não herdava as variáveis privadas configuradas pelo bootstrap, que é iniciado como subprocesso. O runner agora configura esses caminhos antes do `pip`, e o tratamento de erro preserva o `stderr` em vez de gerar um `AttributeError`. Isso mantém o Odoo em container, o runner de aplicação sem alterações e as bibliotecas isoladas do sistema. Rode `ide-test-day.sh` antes da próxima tentativa para garantir que `libcairo2-dev` esteja no prefixo nativo.

As referências dos componentes confirmam esses requisitos: o pacote `wkhtmltopdf` está disponível no Ubuntu Noble ([pacote Ubuntu](https://packages.ubuntu.com/noble/wkhtmltopdf)) e a documentação do ReportLab orienta instalar o extra `pycairo` para renderização bitmap nas versões acima de 4.0.4 ([instalação oficial do ReportLab](https://docs.reportlab.com/install/open_source_installation/)).

## Referência de versões e compatibilidade

O runner usa a versão Odoo do checkout presente na raiz, Python 3.12 ou superior, dependências de `requirements.txt` limitadas por `constraints-voigt.txt`, bibliotecas nativas preparadas para o sistema atual e a imagem PostgreSQL `postgres:16-bookworm` descrita em `compose.yaml`. A configuração IntelliJ usa o plugin Python instalado no IDE; o plugin Odoo pode continuar habilitado para recursos de edição, mas não é necessário para executar testes. Para inventariar versões e comparar outro computador, consulte a seção **Versões de referência e compatibilidade entre computadores** em [README.md](README.md).
