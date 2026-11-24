# Processo de Recrutamento Voigt

Addon customizado para Odoo 20.0 que complementa o aplicativo **Recrutamento** com controles do processo admissional da Voigt.

## Objetivos

O módulo mantém o fluxo Kanban e os cadastros nativos do Odoo e adiciona:

- requisição de vaga baseada no RQ 077, com aprovações distintas do setor e diretoria;
- perfis de vaga Voigt e critérios de avaliação por perfil;
- avaliações de RH, técnica, diretoria, QAE 01/02, organizacional e experiência;
- cálculo de resultado QAE com nota e corte configuráveis; aprovação condicional com justificativa e aprovador diferente do avaliador;
- checklist de admissão baseado no RQ 052, com verificação auditável e dispensa justificada;
- registro restrito de aptidão ocupacional e bloqueio de etapas sem resultado apto;
- integração RQ 006 com treinamentos, responsável operacional, habilidades/atitudes e liberação PRÁTICO;
- controles de passagem configuráveis em estágios nativos de recrutamento.

O addon estende `hr.job`, `hr.applicant` e `hr.recruitment.stage` sem alterar o código do Odoo. Os templates iniciais são uma base configurável e não substituem a validação de RH, DP, Qualidade ou Saúde Ocupacional sobre as revisões vigentes dos documentos Voigt.

## Compatibilidade

- Odoo **20.0**.
- Dependência direta: `hr_recruitment` (o módulo nativo gerencia as dependências de RH necessárias).
- Implantação em Odoo.sh ou Odoo self-hosted/on-premise. Addons com código Python não podem ser instalados diretamente no Odoo Online.
- Licença declarada no manifesto: LGPL-3.

## Instalação

### Repositório local

O diretório `addons/` deste repositório já está incluído no caminho de addons da configuração local. Para instalar em uma base descartável nova pelo runner usado no IDE:

```bash
set -a
source local-infra/.local/ide-runner.env
set +a
PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
  --http-interface=127.0.0.1 --http-port=8070 \
  -d voigt_hr_recruitment_install_test \
  --init=voigt_hr_recruitment --stop-after-init
```

Para iniciar a interface na mesma base, execute o runner sem `--stop-after-init`:

```bash
set -a
source local-infra/.local/ide-runner.env
set +a
PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
  --http-interface=127.0.0.1 --http-port=8070 \
  -d voigt_hr_recruitment_install_test
```

Acesse `http://127.0.0.1:8070`. Inicie primeiro o PostgreSQL local do projeto. Use um nome de banco que possa ser descartado; não execute a instalação ou testes em base produtiva.

### Odoo self-hosted/on-premise

1. Copie/versione a pasta `voigt_hr_recruitment/` em um diretório raiz de addons customizados, por exemplo `/opt/odoo/custom-addons/voigt_hr_recruitment/`.
2. Adicione `/opt/odoo/custom-addons` à opção `addons_path` da configuração do Odoo, mantendo também os diretórios padrão de addons, e reinicie o serviço.
3. Em uma base de desenvolvimento/staging, instale pelo comando abaixo (ajuste configuração, caminho do executável e nome da base):

   ```bash
   ./odoo-bin -c /etc/odoo.conf -d voigt_recruitment_test \
     --init=voigt_hr_recruitment --stop-after-init
   ```

4. Ou instale pela interface: habilite modo desenvolvedor, acesse **Aplicativos > Atualizar lista de aplicativos > Atualizar**, remova o filtro **Aplicativos**/selecione **Extra**, pesquise **Voigt Recruitment Process** e clique em **Ativar**.

### Odoo.sh

Inclua o addon em um repositório/branch conectado ao projeto Odoo.sh. Publique primeiro em uma branch de desenvolvimento, atualize a lista de Apps e instale em base de teste. Promova para staging e valide o processo antes de produção. Odoo.sh detecta addons incluídos no repositório. Não foi realizada implantação Odoo.sh nesta entrega.

### Atualização

Faça backup/snapshot antes de atualizar qualquer base com dados. Com o código já presente no `addons_path`, atualize a base de teste com:

```bash
./odoo-bin -c /etc/odoo.conf -d voigt_recruitment_test \
  --update=voigt_hr_recruitment --stop-after-init
```

No ambiente local, use o runner e o arquivo `ide-runner.env` como nos exemplos anteriores. Pela interface, abra o menu do addon em **Aplicativos** e selecione **Upgrade**. Faça upgrade e eventual desinstalação somente após validar os efeitos na cópia; a remoção de um módulo pode apagar registros relacionados.

## Configuração inicial

### Usuários e grupos

Em **Configurações > Usuários**, atribua os grupos conforme a matriz aprovada pela Voigt:

| Grupo | Uso |
|---|---|
| `Recruitment / User` (`hr_recruitment.group_hr_recruitment_user`) | Acesso padrão ao recrutamento e ao menu de solicitações RQ 077. A aba Voigt no cadastro do candidato está restrita ao Voigt Recruitment Manager nesta versão. |
| `Voigt Recruitment Manager` | Aprovações Voigt, templates, operações de checklist, integração e decisões PRÁTICO/finais. Herda o gerente de recrutamento do Odoo. |
| `Voigt Occupational Health` | Leitura/edição do modelo restrito de aptidão; não dá acesso a `hr.applicant` nem permite criar solicitação de exame. O recrutamento autorizado cria a solicitação. |
| `Voigt Organizational Psychologist` | Acesso a campos e avaliações organizacionais conforme a matriz de acesso. Acesso a candidatos e o fluxo operacional precisam ser validados em UAT. |

Não conceda grupo de gerente ou acesso amplo a candidatos apenas para contornar uma permissão. No comportamento atual, use um Voigt Recruitment Manager para operar checklist e avaliações na aba Processo Voigt; use o grupo de Saúde Ocupacional apenas no menu de aptidão. Teste as permissões com contas de cada papel antes de ativar o processo.

### Estágios do recrutamento

O addon não cria nem renomeia os estágios nativos. Em **Recrutamento > Configuração > Estágios**, edite os estágios existentes, associe vagas no campo nativo de vagas específicas e escolha o campo **Controle de passagem Voigt**:

| Controle | Regra antes de entrar na etapa |
|---|---|
| Sem bloqueio Voigt | Nenhuma validação extra do addon. |
| Exige avaliação RH aprovada | Precisa existir avaliação RH com resultado Apto ou Liberado condicional. |
| Exige entrevista técnica aprovada | Precisa existir avaliação técnica com resultado Apto ou Liberado condicional. |
| Exige documentos e aptidão ocupacional | Todos os itens obrigatórios precisam estar verificados/dispensados, e a aptidão atual precisa ser Apto. |
| Exige aprovação RQ 077, documentos e aptidão | Exige RQ 077 aprovada vinculada à vaga, checklist obrigatório completo e aptidão Apto. |

As validações são feitas no servidor ao gravar a etapa. A equipe de RH deve mapear seus estágios reais para essas travas e testar as transições. Não aplique um gate a uma etapa usada por vagas que não adotam essa regra sem validar o efeito.

### Perfis e templates

Na vaga, selecione **Perfil do processo Voigt**:

- Administrativo;
- Auxiliar de Produção - Rebarbação;
- Auxiliar de Produção - Moldagem;
- Mecânico de Manutenção;
- Outro.

Revise os menus **Processo Voigt > Modelos do checklist**, **Critérios por perfil** e **Habilidades e atitudes RQ 006**. Os registros carregados inicialmente são exemplos baseados nos documentos consultados. Ajuste-os às revisões aprovadas antes de uso real. Critérios técnicos do Mecânico e de Produção são gerados a partir do perfil da vaga.

## Guia de uso do processo

### 1. Abrir e aprovar uma solicitação RQ 077

1. Acesse **Recrutamento > Processo Voigt > Solicitações RQ 077** e crie uma solicitação.
2. Informe empresa, departamento, cargo, quantidade, tipo (efetivo, temporário ou estagiário), motivo, justificativa, jornada e referência salarial. Se o motivo for substituição, informe quem/cargo será substituído.
3. Use **Enviar para aprovação**. O aprovador do setor usa **Aprovar setor**; o solicitante não pode aprovar a própria solicitação. Com gestor do departamento configurado, ele deve aprovar, salvo autorização do grupo Voigt Manager.
4. Um segundo usuário, diferente do solicitante e do aprovador do setor, usa **Aprovar diretoria**. Para rejeitar, preencha o motivo e use **Rejeitar**.

Alterações materiais em uma solicitação já aprovada retornam a solicitação para rascunho e limpam as aprovações anteriores. A vaga não é criada automaticamente.

### 2. Criar a vaga e associar candidatos

Depois da aprovação da RQ, crie a vaga pelo aplicativo Recrutamento, vincule a **Solicitação RQ 077** aprovada, configure empresa/departamento/responsável e selecione o perfil Voigt. Publique conforme o procedimento da empresa.

Cadastre cada candidatura usando o fluxo nativo e associe-a à vaga. O addon cria automaticamente os itens ativos do checklist que sejam globais (`all`) ou do perfil da vaga. O usuário ainda deve registrar avaliações e evidências; o addon não importa currículos ou preenche pareceres.

### 3. Registrar avaliações e resultados

Com usuário Voigt Manager, abra a aba **Processo Voigt** do candidato e adicione avaliações em **Avaliações**. Selecione RH, técnica, diretoria, QAE 01, QAE 02, organizacional ou experiência e confirme avaliador, data e revisão.

- **QAE 01/02:** informe a nota total obtida na aplicação da rubrica aprovada, máximo (padrão 100) e corte (padrão 60). Clique **Calcular resultado**. A nota igual/acima do corte resulta em Apto; abaixo, Inapto. O addon não corrige respostas.
- **Entrevista/avaliação não QAE:** avaliador indicado ou Voigt Manager usa **Marcar apto** ou **Marcar inapto**. Uma avaliação técnica cria linhas de critério do perfil para preencher evidências e notas.
- **Aprovação condicional:** Voigt Manager informa justificativa e registra a aprovação. O aprovador não pode ser o avaliador.

Para mover o candidato a estágio com gate RH/técnico, o resultado correspondente deve ser Apto ou Liberado condicional. Agendas, reuniões e retornos devem ser geridos pelo fluxo nativo; este addon não gera reuniões ou e-mails automáticos.

### 4. Completar documentos e aptidão

1. Com usuário Voigt Manager, no **Checklist de admissão**, altere o item para Solicitado e depois Recebido conforme o processo. Com o documento recebido, clique **Verificar** para registrar usuário e horário.
2. Itens opcionais não bloqueiam a etapa. Itens obrigatórios devem estar Verificados ou Dispensados. A dispensa exige motivo e papel Voigt Manager.
3. Voigt Manager solicita aptidão ocupacional no bloco correspondente do candidato. A equipe autorizada abre **Processo Voigt > Avaliações de aptidão** e usa **Registrar apto** ou **Registrar inapto**.
4. O módulo guarda somente a conclusão e metadados de auditoria no modelo restrito. Não registre diagnóstico, exame, prontuário ou detalhe clínico em campos ou chatter.

Os gates de admissão e proposta exigem resultado ocupacional Apto. O grupo de saúde não tem permissão de leitura do candidato; não conceda essa permissão para facilitar o fluxo sem aprovação formal da matriz de acesso.

### 5. Proposta, contratação e RQ 006

Antes de uma etapa de proposta, associe a vaga à RQ 077 aprovada e finalize checklist obrigatório e aptidão. O addon não gera proposta, contrato ou datas contratuais de 45+45 dias.

Quando a candidatura for movida a uma etapa nativa marcada como **Hired Stage/Etapa contratada**, será criado um registro único **Integração RQ 006**. A integração relaciona-se ao candidato e ao empregado nativo, se o fluxo de contratação tiver criado esse vínculo.

Um usuário Voigt Manager abre **Recrutamento > Processo Voigt > Integração RQ 006** e:

1. confirma admissão e responsável operacional (líder/Anjo da Guarda);
2. registra conclusão dos treinamentos de RH, Qualidade, Segurança, operação e entrega de documentos técnicos;
3. preenche requisitos do perfil: tarefa e EPIs em Rebarbação/Moldagem; treinamento de equipamentos/rotinas no perfil Mecânico;
4. confere as datas de avaliação, que por padrão são 15 dias e 30 dias após admissão, e ajusta conforme procedimento vigente;
5. avalia as nove habilidades e dez atitudes com escala 0, 1, 3 ou 5, registrando notas e evidências;
6. usa **Aprovar liberação PRÁTICO** somente após realizar os treinamentos gerais e específicos exigidos;
7. após completar todas as 19 notas, registra **Efetivar**, **Acompanhar / adequar** ou **Encerrar**.

As datas são editáveis, e o módulo não agenda atividades. Os documentos divergem entre uma semana completa (PO 017) e 15–30 dias (RQ 006); confirme o prazo aprovado com RH/Qualidade.

## Limites e cuidados

- O módulo não cria automaticamente estágios, vagas, propostas, contratos, reuniões ou e-mails.
- QAE registra a pontuação total inserida pelo avaliador; não interpreta respostas.
- Templates/checklists iniciais são intencionalmente mínimos e precisam de revisão por RH/DP e SGQ.
- Não são critérios automáticos: idade, estado civil, filhos, moradia, aparência ou condição clínica. Experiência com lixadeira para Rebarbação é diferencial, não eliminatório.
- Teste permissões, gates e atualização em staging com dados sintéticos. O relatório completo de implementação e decisões está em [`doc/voigt/relatorio_implementacao_voigt_hr_recruitment.md`](../../doc/voigt/relatorio_implementacao_voigt_hr_recruitment.md).

## Testes do addon

Para executar os testes Odoo na base descartável local:

```bash
set -a
source local-infra/.local/ide-runner.env
set +a
PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
  --http-interface=127.0.0.1 --http-port=8070 \
  -d voigt_hr_recruitment_install_test \
  --update=voigt_hr_recruitment \
  --test-enable --test-tags /voigt_hr_recruitment --stop-after-init
```

O teste deve ser executado em banco de desenvolvimento, nunca em produção. O relatório de implementação registra os testes já executados e seus resultados.

## Referências Odoo

- [Instalar e atualizar Apps/módulos](https://www.odoo.com/documentation/20.0/applications/general/apps_modules.html)
- [Criar módulos no Odoo.sh](https://www.odoo.com/documentation/20.0/administration/odoo_sh/create_module.html)
- [Manifesto de módulo](https://www.odoo.com/documentation/20.0/developer/reference/backend/module.html)
- [Segurança do backend](https://www.odoo.com/documentation/20.0/developer/reference/backend/security.html)
- [ORM](https://www.odoo.com/documentation/20.0/developer/reference/backend/orm.html)
- [Testes unitários Odoo](https://www.odoo.com/documentation/20.0/developer/tutorials/unit_tests.html)
