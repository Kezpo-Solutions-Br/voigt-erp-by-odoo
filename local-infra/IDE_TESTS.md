# Runner de testes da plataforma Odoo pelo IntelliJ

Este documento descreve as configurações IntelliJ **Voigt Odoo Local (Testes da Plataforma)** e **Voigt Odoo Local (Testes voigt_hr_recruitment)**, os artefatos que compartilham e como executar os testes oficiais do checkout local. Os runners executam o `odoo-bin` e os módulos presentes neste repositório; não usam a imagem Odoo do Compose para executar os testes.

Use a configuração da plataforma para a suíte `standard` de todos os módulos. Use a configuração `voigt_hr_recruitment` para selecionar exclusivamente os testes desse addon. As duas configurações usam o mesmo runner Python, `.venv`, PostgreSQL, banco temporário e diretório local de dados. Cada execução recria e remove o banco reservado, então execute uma configuração por vez.

A nova configuração não inicia outro Odoo nem mantém outro banco de testes. O runner da aplicação e os dois runners de teste usam o mesmo marcador `local-infra/.local/ide-runner.pid`, portanto uma segunda execução é recusada enquanto a primeira está ativa. O runner da aplicação continua usando `ide-odoo.conf`, `local-infra/data/ide-runner` e o banco configurado para a aplicação; os testes usam `ide-tests.conf`, `local-infra/data/ide-tests` e somente `voigt_ide_tests`.

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
| `.idea/runConfigurations/Voigt_Odoo_IDE_Test_voigt_hr_recruitment.xml` | Segunda configuração IntelliJ, apontando para o mesmo script e ambiente e definindo `ODOO_IDE_TEST_MODULE=voigt_hr_recruitment`. | Permite executar somente os testes marcados pelo Odoo para esse módulo sem duplicar scripts ou dependências. |
| `local-infra/ide-runner/odoo_ide_test_runner.py` | Valida Python e bibliotecas nativas, sincroniza dependências, garante PostgreSQL local, protege a execução concorrente, recria o banco temporário com `odoo-bin db init`, instala/atualiza o escopo necessário, inicia os testes Odoo e remove banco/filestore ao final. | O código de apoio fica isolado do código oficial em `odoo/`, `addons/` e `odoo-bin`. `runpy` executa o comando de testes no mesmo processo iniciado pelo IntelliJ, mantendo breakpoints disponíveis. A variável opcional `ODOO_IDE_TEST_MODULE` escolhe o tag `/modulo` e faz `--init` instalar esse addon e as dependências declaradas; sem ela, o runner mantém `--init=all` e `+standard`. |
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
- O preparo nativo disponibiliza as bibliotecas de relatório no prefixo `local-infra/.local/native` e extrai o pacote oficial `wkhtmltox 0.12.6.1-3` com patched Qt em `local-infra/.local/tooling/wkhtmltox`. O arquivo é validado por SHA-256; o binário privado tem prioridade no `PATH` e suas bibliotecas são acrescentadas ao caminho local do carregador. Nada é instalado globalmente.
- A `.venv` compartilhada recebe `reportlab[pycairo]==4.1.0` sob demanda pelo runner de testes. ReportLab 4.1 não inclui por padrão o backend de renderização de bitmap usado pelo teste de código de barras; essa extensão não altera os requisitos do servidor Odoo em container.
- Quando o `pip` compila PyCairo, o runner passa os diretórios privados de `pkg-config`, headers e bibliotecas ao processo de build. Para que o carregador dinâmico reconheça bibliotecas privadas, ele relança a si mesmo uma vez se esses caminhos não estavam ativos desde o início do processo.
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

2. No IntelliJ, selecione **Voigt Odoo Local (Testes da Plataforma)** para executar a suíte completa, ou **Voigt Odoo Local (Testes voigt_hr_recruitment)** para executar apenas o addon. Clique em **Run** ou **Debug**; coloque breakpoints nos testes ou no código do addon/Odoo.
3. Acompanhe a saída no painel Run/Debug. O processo cria uma base limpa e executa os testes selecionados: `standard` na suíte completa ou o tag de módulo `/voigt_hr_recruitment` na configuração específica. Na execução específica, o addon e suas dependências são instalados para que os testes possam ser descobertos. O Odoo ainda pode carregar testes auxiliares de módulos dependentes durante a inicialização; o resumo deve mostrar os testes do addon selecionado. O banco temporário e seu filestore são removidos ao fim.
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
| Configuração não aparece no IntelliJ | XML ainda não foi recarregado pelo IDE, ou `.idea/runConfigurations` não está versionado/visível. | Reabra o projeto ou use **Run > Edit Configurations** e confirme os arquivos `Voigt_Odoo_IDE_Tests.xml` e `Voigt_Odoo_IDE_Test_voigt_hr_recruitment.xml`. |
| Configuração específica termina sem encontrar testes do addon | O Odoo seleciona testes pelo tag do módulo e só executa arquivos de teste descobertos pelo próprio addon. | Confirme que `addons/voigt_hr_recruitment` contém testes Python importados por `tests/__init__.py` e que os casos são classes compatíveis com o framework Odoo. A configuração seleciona o tag `/voigt_hr_recruitment`; ela não inventa testes ausentes. |
| `Please select a valid Python interpreter` | O SDK selecionado não existe neste checkout ou está associado a outro ambiente. | Execute `ide-test-first-run.sh`, depois selecione `$PROJECT_DIR$/.venv/bin/python`, o mesmo interpretador configurado no runner Odoo. |
| O runner de testes informa que outro interpretador foi selecionado | A configuração de testes está usando um Python diferente do runner Odoo já funcional. | Edite somente a configuração de testes e selecione `$PROJECT_DIR$/.venv/bin/python`; não crie nem selecione uma segunda `.venv`. |
| Runner informa Python abaixo de 3.12 | A configuração iniciou com Python global antigo. | Troque o interpretador para `.venv/bin/python`; Odoo deste checkout requer Python 3.12 ou superior. |
| `libpq.so.5` ausente ou `LD_LIBRARY_PATH` não carregado | Bibliotecas privadas não foram preparadas ou o IntelliJ não leu o arquivo `ENV_FILES`. | Execute `ide-first-run.sh` e `ide-test-day.sh`; confirme `ENV_FILES` apontando para `$PROJECT_DIR$/local-infra/.local/ide-runner.env` e recarregue a configuração. |
| Testes de relatório dizem `Unable to find the pdf engine` | O runner local não encontrava `wkhtmltopdf`, embora a imagem Docker do Odoo já o instale. | Execute `./local-infra/scripts/ide-test-day.sh` para extrair o binário e as fontes no prefixo privado; não é necessário mudar a imagem nem instalar no sistema. |
| `test_report_icon_is_a_glyph` gera PDF, mas não encontra `MaterialSymbols` | O `wkhtmltopdf` dos repositórios Ubuntu não usa o Qt corrigido necessário ao suporte de fontes WOFF. O PDF pode ser criado sem incorporar as fontes do Odoo. | Execute `./local-infra/scripts/ide-test-day.sh`; ele prepara o build oficial `0.12.6.1-3` com patched Qt em área privada e valida sua versão antes de iniciar o runner. |
| `test_render_barcode` falha ao carregar `renderPM`/`rlPyCairo` | O pacote base ReportLab 4.1 não instala o backend Cairo opcional usado para renderizar imagens de código de barras. | Execute novamente o runner de testes; ele instala `reportlab[pycairo]==4.1.0` na `.venv` compartilhada e usa Cairo do prefixo nativo privado. |
| `test_report_error_cleanup` falha junto com erros de PDF | O teste espera que a geração do relatório alcance a etapa de limpeza; sem `wkhtmltopdf`, ela falha antes dessa etapa. | Corrija a disponibilidade do mecanismo PDF conforme acima e rode a suíte novamente. |
| Preparação informa `Dependency "cairo" not found` ao instalar PyCairo | O backend precisa compilar a extensão, mas o processo do `pip` não recebeu o caminho privado do arquivo `cairo.pc` ou o pacote `libcairo2-dev` não está no prefixo. | Execute `./local-infra/scripts/ide-test-day.sh` para atualizar o prefixo e rode novamente. O runner passa `PKG_CONFIG_PATH`, headers e bibliotecas locais ao build; não instale `libcairo2-dev` globalmente. |
| `pkg-config` encontra Cairo, mas a compilação falha em `fatal error: cairo.h: No such file or directory` | O arquivo privado `cairo.pc` declara include paths absolutos do sistema, enquanto os headers estão no prefixo privado. | O runner acrescenta o diretório privado `usr/include/cairo` ao `CPATH`; não usa sysroot, para preservar os headers do Python e as dependências de build do host. |
| Erro termina em `AttributeError: 'NoneType' object has no attribute 'strip'` durante preparação | Um erro de dependência do subprocesso não capturava `stderr`, e o tratamento tentava lê-lo como texto, ocultando o erro inicial. | A versão corrigida exibe a saída do `pip` e a orientação para conferir Cairo/`pkg-config`. Resolva o erro inicial mostrado antes do traceback. |
| Docker indisponível ou PostgreSQL não saudável | Engine parado, credenciais inválidas, porta ocupada ou falha de inicialização. | Inicie Docker, confira `local-infra/.env`, execute `./local-infra/scripts/status.sh` e consulte `./local-infra/scripts/logs.sh db`. |
| Primeiro uso informa volume existente sem `POSTGRES_PASSWORD` válido | O arquivo de ambiente foi apagado ou ainda contém valor de exemplo, embora haja dados PostgreSQL persistidos. | Restaure a credencial original de `local-infra/.env` a partir de uma cópia segura. O wrapper não inventa outra senha nem remove o volume. |
| Test runner recusa iniciar por Odoo Compose ativo | Os dois processos disputariam o mesmo PostgreSQL. | Pare o serviço com `./local-infra/scripts/stop.sh` ou execute `ide-test-day.sh`, que para somente o Odoo em Compose. |
| Mensagem de outro runner ativo | A aplicação Odoo da IDE ou outra execução de testes ainda está ativa. | Pare-a na janela Run/Debug antes de iniciar outra configuração. Se o processo terminou abruptamente, verifique o PID em `local-infra/.local/ide-runner.pid`; os scripts removem marcadores obsoletos quando podem confirmar que o PID não existe. |
| Falha durante instalação de módulo/teste | Dependência externa do teste ausente, falha real de teste ou incompatibilidade da árvore atual. | Leia o primeiro traceback e o resumo de falhas no painel Run; instale/configure apenas o serviço explicitamente exigido pelo teste ou corrija o código e rode novamente. O banco é recriado em cada execução. |
| Runner termina, mas aparece aviso ao remover banco | PostgreSQL foi parado ou ficou indisponível durante a limpeza. | Inicie o banco e rode novamente; o próximo ciclo descarta e recria `voigt_ide_tests`. Não remova outros bancos. |

## Análise da execução reportada

A primeira execução mostrou que o PostgreSQL conectou, o banco temporário foi criado, os módulos carregaram e o runner executou 1.041 testes. Portanto, a falha não ocorreu na configuração da base ou na inicialização do Odoo. O resumo final apontou seis erros de relatório/PDF e uma falha em `test_report_error_cleanup`:

- Os erros de `test_report_icon_is_a_glyph`, relatórios agregados e recarga de anexos dizem explicitamente `Unable to find the pdf engine`. O processo local não tinha `wkhtmltopdf` no `PATH`. O `Dockerfile` já declara esse binário e as quatro famílias de fontes, mas o prefixo nativo do host não as preparava.
- `test_render_barcode` falha ao renderizar um template QWeb. O requisito base fixa ReportLab 4.1.0, mas a extensão opcional de renderização bitmap não é instalada em Linux pelo arquivo de requisitos; o próprio comentário do requisito diz que ela viria do pacote Debian. A execução local usa a `.venv`, não os pacotes Python do container, então esse backend estava ausente.
- `test_report_error_cleanup` é consequência do primeiro problema: sem motor PDF, o fluxo não chega à chamada de exportação que o teste espera verificar.
- Após corrigir o motor PDF, a iteração de teste confirmou que os seis erros e a falha de limpeza desapareceram, mas `test_report_icon_is_a_glyph` falhou porque o PDF não incorporou a fonte Material Symbols. A investigação mostrou que `wkhtmltopdf 0.12.6` do Ubuntu não inclui patched Qt; o projeto Odoo documenta esse requisito para versões atuais ([guia wkhtmltopdf do Odoo](https://github.com/odoo/odoo/wiki/Wkhtmltopdf)). A versão fixada `0.12.6.1-3` é indicada pelo Odoo 16+ e publicada pelo projeto wkhtmltopdf ([release oficial](https://github.com/wkhtmltopdf/packaging/releases/tag/0.12.6.1-3)).
- As mensagens sobre `websocket-client`, `aiosmtpd` e outros módulos ausentes indicam testes ignorados opcionais; elas não explicam os sete resultados do resumo final.

As correções locais preparam Cairo em `local-infra/.local/native` e o build oficial patched Qt em `local-infra/.local/tooling/wkhtmltox`. A iteração autorizada confirmou que `pkg-config` encontrava Cairo, mas seu `cairo.pc` declarava `/usr/include/cairo`, enquanto os headers estavam no prefixo privado. Uma tentativa de sysroot redirecionou também includes do Python e de dependências XCB; foi removida em favor de adicionar diretamente o diretório privado de headers Cairo. O backend ReportLab instalou. A raiz do checkout foi adicionada a `sys.path` para iniciar `odoo-bin` via `runpy`, e o runner se relança quando necessário para que o carregador dinâmico reconheça as bibliotecas privadas desde a inicialização do processo. Uma execução completa posterior passou pelos erros de PDF, limpeza e código de barras; restou a falha Material Symbols, causada pelo binário Ubuntu sem patched Qt. O bootstrap agora baixa o pacote oficial fixado, confere SHA-256 e prioriza esse binário privado.

A validação final após essas mudanças executou **1.041 testes: 0 falhas e 0 erros**. `test_report_icon_is_a_glyph`, `test_report_error_cleanup` e `test_render_barcode` passaram; testes opcionais que dependem de bibliotecas ausentes continuam sendo marcados como ignorados pelo Odoo. Durante essa preparação também foi corrigida a detecção APT em hosts multiarch: cada status agora é lido em uma linha, para que entradas amd64/i386 existentes não sejam interpretadas como pacote ausente nem provoquem uma atualização APT desnecessária.

Após adicionar a configuração `voigt_hr_recruitment`, validei novamente ambos os modos: o runner direcionado reportou **12 testes do módulo, 0 falhas e 0 erros**; em seguida, a configuração padrão reportou **1.041 testes, 0 falhas e 0 erros**. Isso confirma que, sem `ODOO_IDE_TEST_MODULE`, a configuração existente continua usando `--init=all` e `--test-tags=+standard`.

As referências dos componentes confirmam esses requisitos: o pacote `wkhtmltopdf` está disponível no Ubuntu Noble ([pacote Ubuntu](https://packages.ubuntu.com/noble/wkhtmltopdf)) e a documentação do ReportLab orienta instalar o extra `pycairo` para renderização bitmap nas versões acima de 4.0.4 ([instalação oficial do ReportLab](https://docs.reportlab.com/install/open_source_installation/)).

## Referência de versões e compatibilidade

O runner usa a versão Odoo do checkout presente na raiz, Python 3.12 ou superior, dependências de `requirements.txt` limitadas por `constraints-voigt.txt`, bibliotecas nativas preparadas para o sistema atual e a imagem PostgreSQL `postgres:16-bookworm` descrita em `compose.yaml`. A configuração IntelliJ usa o plugin Python instalado no IDE; o plugin Odoo pode continuar habilitado para recursos de edição, mas não é necessário para executar testes. Para inventariar versões e comparar outro computador, consulte a seção **Versões de referência e compatibilidade entre computadores** em [README.md](README.md).
