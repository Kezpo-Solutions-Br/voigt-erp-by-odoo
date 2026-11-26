# Relatório de implementação - `voigt_hr_recruitment`

**Data:** 24 de novembro de 2026  
**Idioma:** português do Brasil  
**Repositório/versão:** checkout local Odoo 20.0, `version_info = (20, 0, 0, FINAL, 0, '')`  
**Addon:** `addons/voigt_hr_recruitment`

## 1. Objetivo e resultado

Foi implementado um addon isolado para acrescentar ao Recrutamento do Odoo os controles documentados para o processo admissional da Voigt. A extensão usa os modelos nativos `hr.job`, `hr.applicant` e `hr.recruitment.stage`; os arquivos do core não foram alterados.

O addon cobre requisição RQ 077 e aprovações, etapas bloqueáveis, avaliações e rubricas por perfil, checklist de admissão, registro mínimo de aptidão ocupacional, integração RQ 006, avaliação de habilidades/atitudes e liberação PRÁTICO. O resultado é uma base funcional e testada em um banco local descartável; ainda requer validação de RH, DP, Segurança/medicina do trabalho e Qualidade antes de ser adotado em processo real.

## 2. Fontes consideradas

Foram extraídos os conteúdos das fontes SGQ e dos documentos de posições existentes em `ArtefatosVoigt/0-PROCESSO_ADMISSIONAL`, além do relatório técnico existente em `doc/voigt/relatorio_recrutamento_voigt_odoo.md`.

- **PO 017 - Admissão, Demissão e Treinamento, Rev. B, 28/10/2020:** sequência RQ 077, triagem, entrevistas, exame ocupacional, RQ 052, socialização, RQ 006, acompanhamento e contratação.
- **RQ 077 - Solicitação de Admissão, Rev. A, 29/10/2020:** cargo, tipo, motivo, justificativa, substituição, horário, referência salarial, responsável do setor e diretor.
- **RQ 052 - Documentos para Admissão, Rev. B, 29/10/2020:** checklist de documentação e verificação pelo RH/DP.
- **RQ 079 - QAE 01, Rev. B:** questionário para escolaridade fundamental incompleta, total de 100 pontos, aprovação a partir de 60 e liberação condicional com justificativa e aprovação autorizada.
- **RQ 081 - QAE 02, Rev. B:** questionário para escolaridade fundamental completa, total de 100 pontos, corte de 60 e regra de liberação condicional equivalente.
- **RQ 006 - Treinamento Introdutório, Rev. A, 07/07/2020:** treinamento de RH, Qualidade, Segurança e operação; líder/Anjo da Guarda; 9 habilidades, 10 atitudes; escala 0/1/3/5; item PRÁTICO.
- **Vaga Auxiliar de Produção - atualizada em 08/01/2026:** diferenças entre Rebarbação e Moldagem, tarefas e equipamentos de cada setor, segurança e treinamento do posto.
- **Vaga Mecânico de Manutenção e roteiro de entrevista:** perfil generalista e critérios técnicos de manutenção, como solda, caldeiraria, desenho, lixadeira, hidráulica, elétrica, rolamentos, torno, fresa, medição, ponte rolante e manutenção predial.

Parte dos formulários SGQ está em revisão/uso documental desde 2020. A pasta também contém cópias antigas, revisões marcadas como obsoletas, formulários preenchidos com dados de funcionários e perguntas antigas de entrevista. Os dados individuais não foram importados e campos potencialmente discriminatórios foram excluídos dos critérios digitais.

## 3. Decisões de projeto

### 3.1 Módulo independente e extensível

O módulo depende somente de `hr_recruitment`, que já depende de `hr`. As regras ficam em modelos próprios e extensões pequenas (`_inherit`), carregadas pelo manifesto e separadas em `models/`, `views/`, `data/`, `security/` e `tests/`. Isso mantém o core inalterado e permite atualizar/configurar o addon sem copiar a implementação nativa.

Os modelos de templates para documentos e critérios permitem alterar checklists e rubricas por dados Odoo sem codificar uma nova regra para cada vaga. As etapas continuam sendo as etapas padrão de recrutamento: um administrador associa uma trava Voigt à etapa e usa o campo nativo de vagas da etapa para limitar sua aplicação a cargos específicos.

### 3.2 Requisição e aprovação RQ 077

`voigt.recruitment.request` armazena os dados essenciais da solicitação, número sequencial, empresa, departamento, cargo, motivo, modalidade, justificativa, quantidade, horário e referência salarial. As ações registram separadamente a aprovação do responsável pelo setor e da diretoria com usuário e horário. Usuários regulares não podem aprovar a própria solicitação nem repetir a aprovação nas duas etapas; quando o departamento possui gestor cadastrado, a aprovação do setor deve ser feita por esse gestor ou pelo grupo Voigt autorizado. Para habilitar o teste ponta a ponta com o usuário Administrator, `base.group_system` pode executar ambas as ações e aprovar o próprio registro; cada ação ainda grava usuário e horário. Essa exceção de administrador é ampla e não deve substituir a separação de funções no processo real.

Depois de aprovada, uma alteração material retorna a solicitação para rascunho e limpa as aprovações anteriores. A vaga nativa referencia a RQ 077 aprovada. A criação da vaga continua sendo uma ação do usuário, pois o documento não especifica defaults suficientes para gerar automaticamente todos os campos de uma posição.

### 3.3 Perfil de vaga e avaliação

`hr.job.voigt_profile` diferencia Administrativo, Produção - Rebarbação, Produção - Moldagem, Mecânico de Manutenção e Outro. Para avaliação técnica, critérios do perfil mecânico são gerados de templates com os tópicos observados no roteiro da função. Os critérios de produção distinguem Rebarbação e Moldagem. A experiência prévia com lixadeira está marcada como diferencial, não eliminatório, conforme a descrição da vaga.

As avaliações RH, técnica, diretoria, QAE 01/02, avaliação organizacional e experiência ficam em `voigt.applicant.assessment`. QAE 01 e QAE 02 recebem a revisão Rev. B e corte inicial 60/100. O total é registrado pelo avaliador: o addon não tenta corrigir automaticamente respostas abertas ou interpretar a qualidade de respostas discursivas. Recalcular uma nota após edição a devolve a pendente. A liberação condicional exige motivo e grupo Voigt autorizado; usuários regulares não podem aprovar a própria avaliação, enquanto administradores `base.group_system` podem fazê-lo para exercício de ponta a ponta.

### 3.4 Checklist e passagem de fase

O RQ 052 foi transformado em templates de checklist, associados automaticamente quando a candidatura é criada. O conjunto inicial limita-se a CPF, identificação, endereço, comprovação escolar quando necessária para a vaga e qualificação técnica como item opcional no perfil mecânico. Itens adicionais podem ser configurados pela área responsável.

Essa seleção conservadora evita pré-carregar solicitações antigas de dados de saúde, SUS, votação, raça/etnia, antecedentes e informações familiares sem comprovação da necessidade atual. O sistema registra estado, responsável e horário de verificação. Dispensar um item exige justificativa; itens verificados/dispensados não podem ser apagados. O grupo de recrutamento Voigt Manager tem acesso ao checklist e seus anexos.

Uma etapa marcada com controle Voigt pode exigir avaliação RH aprovada, entrevista técnica aprovada, checklist verificado e aptidão ocupacional. A etapa de proposta exige também requisição RQ 077 aprovada. As validações ficam no servidor, então não dependem somente da interface Kanban.

### 3.5 Aptidão ocupacional e proteção de dados

Foi criado o grupo `Voigt Occupational Health` e um modelo separado (`voigt.occupational.assessment`) para registrar a solicitação e a conclusão. A equipe de saúde não recebe ACL de leitura de `hr.applicant`: vê somente nome, vaga e dados de auditoria expostos no modelo restrito de aptidão. O recrutamento acessa o resultado agregado no candidato como `Não solicitado`, `Pendente`, `Apto` ou `Inapto`; não há campos para diagnóstico ou prontuário. O resultado é gravado por ações autorizadas e mantém responsável/data. As etapas de admissão/proposta exigem `Apto`. A interface orienta expressamente a não incluir informação clínica.

As descrições antigas incluem idade, estado civil, filhos, moradia, barba e uso de óculos. Esses dados não foram adicionados como filtros nem como campos de avaliação. Restrições ocupacionais e adequações devem ser definidas por RH e profissionais de Segurança/Saúde do Trabalho para cada posto, com análise de acessibilidade e da legislação aplicável.

### 3.6 Integração RQ 006 e critérios de função

Ao mover uma candidatura para uma etapa nativa marcada como contratada, o módulo cria um registro `voigt.onboarding`, sem duplicar `hr.employee`; o vínculo com o empregado é relacionado ao `employee_id` da candidatura. O registro acompanha RH, Qualidade, Segurança, operação, instrutor/líder ou Anjo da Guarda, entrega de documentação técnica e os passos específicos do perfil.

Para Rebarbação/Moldagem, a liberação prática requer área compatível com o perfil, treinamento da tarefa do posto e conferência de EPIs. Para Mecânico, exige registro do treinamento aplicável aos equipamentos/rotinas da função. Os treinamentos administrativos, de Qualidade, Segurança, operação, informação documentada e responsável operacional são requisitos gerais para liberar o item PRÁTICO.

O módulo gera as 9 linhas de habilidades e 10 de atitudes do RQ 006 com escala 0, 1, 3 ou 5. A avaliação final (efetivar, acompanhar/adequar ou encerrar) exige todas as linhas avaliadas e grava responsável e horário. A primeira avaliação fica prevista para 15 dias e o acompanhamento intermediário para 30 dias; ambas as datas são editáveis.

**Divergência documental:** PO 017 Rev. B orienta avaliar após uma semana completa; RQ 006 Rev. A indica prazo de 15 a 30 dias. Como os documentos disponíveis não resolvem qual revisão prevalece, o sistema usa 15 dias por ser o valor inicial mais próximo indicado pelo formulário RQ 006 e permite ajuste pelo responsável. RH/Qualidade deve confirmar e atualizar esse padrão antes do piloto.

## 4. Arquivos principais

- `addons/voigt_hr_recruitment/README.md`: objetivo do addon, compatibilidade, instalação, configuração e tutorial operacional em português.
- `__manifest__.py`: dependência, versão, arquivos carregados e licença. Inclui descrição curta explícita para o Apps, evitando que o Odoo use o README Markdown como descrição reStructuredText do módulo.
- `models/voigt_recruitment_request.py`: RQ 077, etapas de aprovação, histórico e reabertura após alteração material.
- `models/voigt_applicant_assessment.py` e `models/voigt_applicant_assessment_criterion.py`: avaliações, QAE, decisões autorizadas e critérios por posição.
- `models/voigt_applicant_document.py` e `models/voigt_applicant_document_template.py`: checklist, evidências, verificação e dispensa com justificativa.
- `models/voigt_onboarding.py`, `models/voigt_onboarding_skill.py` e `models/voigt_onboarding_skill_template.py`: RQ 006, treinamento, critérios, liberação prática e decisão final.
- `models/hr_job.py`, `models/hr_recruitment_stage.py` e `models/hr_applicant.py`: extensões e travas de transição do recrutamento nativo.
- `data/recruitment_data.xml` e `data/recruitment_templates.xml`: sequência RQ 077 e templates iniciais baseados nos documentos.
- `i18n/voigt_hr_recruitment.pot` e `i18n/pt_BR.po`: catálogo extraído pelo exportador Odoo e traduções dos termos ingleses do addon para português do Brasil.
- `security/`: grupo funcional, permissão mínima por modelo e domínios por empresa.
- `views/`: formulários, listas e menus do processo, campos na vaga/candidato/etapa e templates editáveis.
- `tests/test_voigt_recruitment.py`: testes de regras de fluxo e validações.

## 5. Testes e execução local

Os testes usam `BaseCommon` do Odoo, ficam importados em `tests/__init__.py` e são executáveis pela infraestrutura `TransactionCase` do Odoo. Foram exercitados:

- criação e aprovação em duas etapas da solicitação, mudança que exige aprovação nova e bloqueio de alteração direta do estado;
- campos obrigatórios da substituição, aceitação dos valores iniciais `draft` e campos de aprovação vazios enviados pelo formulário;
- fluxo ponta a ponta executado pelo perfil Administrator: requisição e duas aprovações próprias, vaga ligada à RQ, candidatura, gates RH/técnico/admissão/proposta, checklist, aptidão, estágio contratado, integração RQ 006, liberação PRÁTICO e avaliação final;
- exceção de administrador para aprovação condicional própria e resultado ocupacional;
- travas de etapa por avaliação e aptidão, criação automática do checklist e bloqueio de escrita direta no resultado ocupacional;
- cálculo do corte QAE 01, atualização da nota e liberação condicional;
- critérios técnicos gerados para Mecânico;
- recusa de liberação PRÁTICO sem os treinamentos e requisitos do posto;
- checklist de habilidades/atitudes RQ 006 e conclusão da decisão final.

Para rodar os testes, use o runner da configuração `.idea/runConfigurations/Voigt_Odoo_IDE.xml` ou o CLI Odoo com a mesma configuração local. Nesta revisão, o runner interativo já estava ativo, então os testes foram executados por `odoo-bin` no banco descartável `voigt_hr_recruitment_test2`:

```bash
set -a
source local-infra/.local/ide-runner.env
set +a
export PGHOST=127.0.0.1 PGPORT=15432 PGUSER=odoo \
  PGPASSFILE="$PWD/local-infra/.pgpass" \
  ODOO_RC="$PWD/local-infra/.local/ide-odoo.conf" PYTHONPATH="$PWD"
./.venv/bin/python odoo-bin -c "$ODOO_RC" -d voigt_hr_recruitment_test2 \
  --update=voigt_hr_recruitment \
  --test-enable --test-tags /voigt_hr_recruitment --stop-after-init --http-port=8071
```

**Resultado final:** após as correções de criação de RQ e do perfil de administrador, 16 testes do módulo executados; `0 failed, 0 error`. A suíte cobre o cenário do tutorial ponta a ponta com Administrator, incluindo criação inicial no estado draft, aprovações próprias da RQ 077, vaga, candidatura, gates, checklist, aptidão, contratação, onboarding e avaliação final. Também confirma que um usuário de Saúde Ocupacional sem recrutamento não pode consultar `hr.applicant`. Passaram ainda a compilação Python e a leitura sintática dos XML do addon. A atualização carregou views, ACLs, templates, modelos e `pt_BR.po` no Odoo 20.0, sem avisos de renderização da descrição do módulo. O runner IDE permaneceu ativo e o servidor respondeu em `127.0.0.1:8070`; sem banco selecionado na URL, o endpoint encaminhou para o seletor de bancos (HTTP 303). A execução de testes usou `odoo-bin` com a mesma configuração local e o banco descartável `voigt_hr_recruitment_test2`, pois o runner IDE já estava ocupado pela instância interativa.

Os avisos de `pdfminer.six` e `markdown2` ausentes vêm do ambiente de desenvolvimento e não impediram a instalação nem os testes do addon. Não foi feita validação visual interativa de cada view no navegador.

## 5.1 Internacionalização e idioma pt_BR

O screenshot apresentado mostrou cabeçalhos nativos das solicitações (“Name”, “Job Title”, “Department”, “Employment Type”, “Requester” e “State”) em inglês. O problema é resolvido pela camada de tradução padrão do Odoo: os rótulos originais dos campos e as mensagens continuam no idioma-fonte do código, e os correspondentes em português do Brasil são fornecidos em `i18n/pt_BR.po`. O arquivo `i18n/voigt_hr_recruitment.pot` foi exportado pelo comando oficial `odoo-bin i18n export` da base Odoo 20 local, cobrindo os termos extraídos de modelos, dados e views.

Para a tradução ser exibida, o idioma Português (Brasil) precisa estar instalado e selecionado na preferência de idioma do usuário que acessa o Odoo. As traduções de módulo são carregadas na instalação/atualização quando o idioma está instalado; por isso o guia inclui instalação do idioma, definição da preferência individual e upgrade do addon. A internacionalização não altera o idioma dos usuários nem força o idioma de toda a base.

Validação feita: ativação de `pt_BR` na base descartável `voigt_hr_recruitment_test2`, carregamento do arquivo pelo comando `i18n loadlang` e inspeção de metadados `fields_get` no ORM com contexto `lang=pt_BR`. Os seis campos visíveis no screenshot foram retornados como `Nome`, `Cargo solicitado`, `Departamento`, `Tipo de contratação`, `Solicitante` e `Estado`. Também foram conferidos `Perfil do processo Voigt` no `hr.job`, `Aptidão ocupacional Voigt` no `hr.applicant`, nome, resumo e descrição do módulo em **Apps**. O `.po` inclui mensagens de modelo, campos, menus e ações; entradas que já são originalmente portuguesas mantêm o texto fonte e podem ter `msgstr` vazio, comportamento normal de gettext/Odoo. A instalação/atualização do módulo também atualiza as traduções dos idiomas instalados conforme a documentação.

Não foi possível usar um Web Inspector da integração IntelliJ disponível nesta sessão: a ferramenta IDE exposta não publicou comandos de navegador/inspeção. O runner local já estava ativo e o banco estava disponível; foi utilizado o ORM Odoo diretamente para confirmar a tradução dos rótulos reportados. A interface web ainda depende de selecionar um banco e autenticar um usuário cuja preferência seja pt_BR.

## 6. Referências usadas na implementação

As referências abaixo foram usadas para extrair o fluxo, definir os requisitos funcionais, entender a plataforma Odoo 20.0 e conferir as convenções de módulo, segurança, testes e implantação. Os documentos corporativos têm revisões e datas diferentes; sua citação registra o material analisado, não confirma vigência.

### 6.1 Fontes Voigt do processo admissional

As fontes estão na pasta [0-PROCESSO_ADMISSIONAL](https://drive.google.com/drive/folders/1KGn9FOOWFUX3dC_PkdashI38_bm5-3Hy) dentro de [ArtefatosVoigt](https://drive.google.com/drive/folders/1xG_JtIWF0sVT45TMwliULYxTrGiJBh_a). Para acesso direto no ambiente local, os nomes correspondem à pasta `/home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/`.

- **PO 017 - Admissão, Demissão e Treinamento - Voigt Rev. B, 28/10/2020**, em [`SGQ/0-Em análise/PO 017 - Admissão, Demissão e Treinamento - Voigt Rev B 28Out2020 OK.xls`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/PO 017 - Admissão, Demissão e Treinamento - Voigt Rev B 28Out2020 OK.xls>): sequência do processo, papéis, registros de recrutamento, aptidão, socialização, acompanhamento e contratação.
- **RQ 077 - Solicitação de Admissão - Voigt Rev. A, 29/10/2020**, em [`SGQ/0-Em análise/RQ 077 - Solicitação de Admissão - Voigt - Rev A 29Out2020 OK.xlsx`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/RQ 077 - Solicitação de Admissão - Voigt - Rev A 29Out2020 OK.xlsx>): abertura de vaga, justificativa, tipo, motivo, horário, referência salarial e aprovações.
- **RQ 052 - Documentos para Admissão - Voigt Rev. B, 29/10/2020**, em [`SGQ/0-Em análise/RQ 052 - Documentos para Admissão - Voigt Rev B 29Out2020.xlsx`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/RQ 052 - Documentos para Admissão - Voigt Rev B 29Out2020.xlsx>): categorias de documentos e conferência admissional; os templates digitais iniciais foram reduzidos deliberadamente por minimização de dados.
- **RQ 079 - Questionário QAE 01 - Voigt Rev. B, 28/10/2020**, em [`SGQ/0-Em análise/RQ 079 - Questionário QAE 01 - Voigt Rev B 28Out2020 OK.xlsx`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/RQ 079 - Questionário QAE 01 - Voigt Rev B 28Out2020 OK.xlsx>): pontuação, total, corte e resultado condicional considerados na implementação.
- **RQ 081 - Questionário QAE 02 - Voigt Rev. B, 29/10/2020**, em [`SGQ/0-Em análise/RQ 081 - Questionário QAE 02 - Voigt Rev B 29Out2020 OK.xls`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/RQ 081 - Questionário QAE 02 - Voigt Rev B 29Out2020 OK.xls>): rubrica da segunda faixa de escolaridade e regra de resultado.
- **RQ 006 - Treinamento Introdutório - Voigt Rev. A, 07/07/2020**, em [`SGQ/0-Em análise/RQ 006 - Treinamento Introdutório - Voigt - Rev A 07Jul20 OK.xlsx`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/SGQ/0-Em análise/RQ 006 - Treinamento Introdutório - Voigt - Rev A 07Jul20 OK.xlsx>): treinamentos, líder/Anjo da Guarda, 9 habilidades, 10 atitudes, escala 0/1/3/5 e item PRÁTICO.
- **08-01-26 Vaga auxiliar de produção - atualizado.docx**, em [`Processos Seletivos/Descrição da vaga/08-01-26 Vaga auxiliar de produção - atualizado.docx`](</home/fernandoavanzo/Voigt/documents/ArtefatosVoigt/0-PROCESSO_ADMISSIONAL/Processos Seletivos/Descrição da vaga/08-01-26 Vaga auxiliar de produção - atualizado.docx>): atividades de Rebarbação e Moldagem, condições do posto e experiência com lixadeira como diferencial, não pré-requisito eliminatório.
- **Perfil da vaga mecânico de manutenção.docx** em `Processos Seletivos/PG/Produção/Mecânico/`, **Vaga mecânico de manutenção 10-2026.docx** em `Processos Seletivos/PG/Produção/Mecânico/2026/` e **Roteiro entrevista para mecânico.docx** em `Processos Seletivos/Grupo Guia RH/Mecânico/`: tópicos de avaliação técnica geral de manutenção usados para criar critérios editáveis por perfil.
- **01-2022 Roteiro para entrevista REV.docx** em `Processos Seletivos/Seleção RH Interno/` e descrições **Rebarbação completo.docx** / **Moldagem completo.docx** em `Processos Seletivos/HR - produção/` e `Processos Seletivos/Imediatta/Produção/Moldagem/`: contexto para etapas e requisitos de entrevistas. Perguntas pessoais antigas não foram transplantadas ao addon.
- **Relatório de aderência e plano funcional anterior**, [relatorio_recrutamento_voigt_odoo.md](/home/fernandoavanzo/Projects/Kezpo/voigt-erp-by-odoo/doc/voigt/relatorio_recrutamento_voigt_odoo.md): análise do Odoo nativo, lacunas do fluxo Voigt, riscos de dados e proposta de addon. Foi usado como insumo, atualizado pelo código efetivamente entregue neste relatório.

A pasta contém também documentos históricos de funcionários, versões antigas/obsoletas, planilhas de controle, propostas de fornecedores e material de divulgação. Esses arquivos foram reconhecidos como contexto do acervo, mas dados pessoais e informações de candidatos/empregados não foram copiados ao código, templates, banco de teste ou relatório. A lista acima delimita os documentos de processo e perfil efetivamente usados como base das regras; não constitui inventário arquivístico integral da pasta.

### 6.2 Código do Odoo e documentação técnica oficial

- [Odoo 20 - documentação de Apps e módulos](https://www.odoo.com/documentation/20.0/applications/general/apps_modules.html): atualizar a lista de Apps, instalar, atualizar e desinstalar módulos; observado o filtro “Extra” para localizar módulos que não são Apps principais.
- [Odoo 20 - criação de módulos no Odoo.sh](https://www.odoo.com/documentation/20.0/administration/odoo_sh/create_module.html) e [implantação de módulos no Odoo.sh](https://www.odoo.com/documentation/20.0/developer/howtos/website_themes/going_live.html): estrutura e distribuição de addons customizados. O guia deste relatório também oferece alternativa self-hosted; este módulo Python não pode ser instalado diretamente no Odoo Online, que não aceita módulos customizados com Python ([limite documentado para Odoo.sh/Odoo Online](https://www.odoo.com/documentation/20.0/administration/odoo_sh/getting_started/create.html)).
- [Odoo 20 - manifesto de módulo](https://www.odoo.com/documentation/20.0/developer/reference/backend/module.html): metadados, dependências, arquivos declarados e licença.
- [Odoo 20 - tutorial de criação de módulos e segurança](https://www.odoo.com/documentation/20.0/developer/tutorials/backend.html): estrutura declarativa, modelos, acesso e herança de views.
- [Odoo 20 - diretrizes de código](https://www.odoo.com/documentation/20.0/contributing/development/coding_guidelines.html): convenções para Python, arquivos de views, dados e estrutura de módulos.
- [Odoo 20 - tradução de módulos](https://www.odoo.com/documentation/20.0/developer/howtos/translations.html): exportação/importação de PO/POT, diretório `i18n/`, extração de rótulos em views/campos e carregamento automático ao instalar idioma e módulo. A recomendação orienta manter o POT do módulo e PO por idioma.
- [Odoo 20 - CLI de internacionalização](https://www.odoo.com/documentation/20.0/developer/reference/cli.html): opções `i18n export` para gerar o catálogo POT a partir do addon instalado.
- [Odoo 20 - tutorial de construção de módulos](https://www.odoo.com/documentation/20.0/developer/tutorials/backend.html): fluxo de desenvolvimento em inglês, exportação gettext POT e produção de traduções PO; menciona a plataforma de traduções Odoo como ambiente colaborativo para os arquivos de módulo.
- [Odoo 20 - ORM e herança](https://www.odoo.com/documentation/20.0/developer/reference/backend/orm.html): modelos/recordsets, extensão por `_inherit`, constraints, `Command`, operações em lote e cache.
- [Odoo 20 - segurança](https://www.odoo.com/documentation/20.0/developer/reference/backend/security.html) e [tutorial para restringir acesso a dados](https://www.odoo.com/documentation/20.0/developer/tutorials/restrict_data_access.html): grupos, ACLs, regras, acesso a campos e validação no servidor.
- [Odoo 20 - arquivos de dados XML](https://www.odoo.com/documentation/20.0/developer/reference/backend/data.html) e [views](https://www.odoo.com/documentation/20.0/developer/reference/user_interface/view_records.html): carga ordenada de dados, menus, ações e herança de views.
- [Odoo 20 pt_BR - adicionar candidatos](https://www.odoo.com/documentation/20.0/pt_BR/applications/hr/recruitment/add_applicants.html): criação manual de candidaturas a partir da vaga ou do formulário geral, preenchimento padrão do cargo/recrutador pela vaga e campos disponíveis no formulário.
- [Odoo 20 pt_BR - fluxo de recrutamento](https://www.odoo.com/documentation/20.0/pt_BR/applications/hr/recruitment/recruitment_flow.html): etapas do processo nativo e caminho da candidatura desde a entrada até a contratação.
- [Odoo 20 - testes unitários](https://www.odoo.com/documentation/20.0/developer/tutorials/unit_tests.html) e [referência do framework de testes](https://www.odoo.com/documentation/20.0/developer/reference/backend/testing.html): organização dos testes no addon, casos transacionais, tags e execução via CLI.
- Código local da série 20.0 usado para compatibilidade: `addons/hr_recruitment/models/hr_applicant.py`, `hr_job.py`, `hr_recruitment_stage.py`, `security/ir.access.csv`, `security/hr_recruitment_security.xml` e views do módulo nativo; também `odoo/release.py` e a configuração `.idea/runConfigurations/Voigt_Odoo_IDE.xml`. O addon declara somente `hr_recruitment` como dependência direta.

As páginas técnicas Odoo foram consultadas em 24/11/2026. A documentação da série 20.0 foi priorizada porque o checkout do repositório identifica Odoo 20.0; em implantação, confirmar que a instância de destino também é 20.0 e consultar a documentação correspondente à sua edição/versão.

## 7. Padrões de projeto, práticas Odoo e justificativas

### 7.1 Fronteira do addon e princípio aberto/fechado

`voigt_hr_recruitment` é uma unidade instalável independente: depende de `hr_recruitment`, mantém os modelos Voigt no namespace `voigt.*` e estende modelos nativos com `_inherit`. Nenhum arquivo do core foi editado. A regra está separada por domínio (`recruitment_request`, `assessment`, `document`, `occupational_assessment`, `onboarding`) e por camada (modelos, segurança, dados, views e testes). Esse desenho concentra alterações no addon, facilita revisão/desinstalação em banco de teste e reduz conflitos em upgrades do core.

O princípio aberto/fechado foi aplicado onde os documentos permitem variação: templates de checklist, critérios técnicos e habilidades/atitudes podem ser parametrizados pelo Odoo, e as etapas nativas recebem um campo de controle. Uma nova vaga ou revisão pode usar/configurar dados existentes sem criar uma subclasse de Python para cada cargo. As regras imutáveis de autorização e bloqueio permanecem no servidor. Não se afirma que toda regra esteja aberta a configuração: categorias de perfil e os gates fazem parte do contrato do addon e uma mudança estrutural neles requer alteração versionada e testes.

### 7.2 Convenções do framework Odoo

- O manifesto declara versão, licença, dependência e ordem explícita de carga, de modo que grupos/ACLs sejam carregados antes de views e estas encontrem modelos já registrados.
- Modelos persistentes herdam `mail.thread` quando trilha de alterações/decisões é útil; relações usam `ondelete`, `required`, `index`, `check_company`, constraints e índice único quando necessário para integridade.
- As extensões usam `@api.model_create_multi`, métodos do ORM, `Command` para linhas relacionadas e ações públicas explícitas em botões, sem SQL direto. Campos derivados usam `compute`/`related` e invalidação de cache quando a aptidão é atualizada por outro modelo.
- As views existentes são herdadas com `inherit_id`; formulários/listas e dados padrão são declarados por XML. A interface melhora operação, mas não é o controle de segurança nem o local único de uma regra.
- Os testes ficam em `tests/`, importados por `tests/__init__.py`, usam ambiente transacional Odoo e são selecionáveis por tag `/voigt_hr_recruitment`.

### 7.3 Integridade do fluxo e desenho de estados

Solicitação, avaliação, checklist, aptidão e integração têm estados explícitos. Transições que representam aprovação são métodos (`action_submit`, `action_approve_department`, `action_approve_director`, `action_evaluate`, `action_verify`, `action_waive`, `action_mark_fit`, `action_approve_practical` e decisões finais), com pré-condições, ator e data. Escrita direta de estado/auditoria protegidos é recusada; alterações materiais em uma solicitação aprovada invalidam aprovações anteriores. Isso protege importações e chamadas ORM, além da tela.

A geração de checklist ocorre na criação da candidatura e a integração ocorre quando a candidatura chega a uma etapa nativa marcada como contratada. O índice único no onboarding evita duplicação do registro por candidatura. Os requisitos de treinamento e de PRÁTICO são checados de novo no momento da ação de liberação, permitindo que o dado da UI não seja a única barreira.

### 7.4 Segurança, privacidade e multiempresa

ACLs, grupos e restrição por empresa foram declarados em `security/`. O grupo de recrutamento Voigt Manager herda o administrador nativo de recrutamento; o grupo ocupacional tem leitura/edição no modelo de aptidão, sem ACL de criação nem de `hr.applicant`; o recrutamento autorizado cria solicitações e o resultado só é gravado por ações restritas. A pedido do usuário, a exceção de `base.group_system` também pode ler o resumo restrito e registrar aptidão, para que o perfil Administrator consiga executar o tutorial inteiro na base de teste. Administradores do sistema devem permanecer limitados a pessoas de confiança; para operação normal, mantenha a Saúde Ocupacional no grupo designado. Parecer psicológico e campos de gestão têm controle por grupos. A limitação de campo com `groups` é reforçada por ACLs/modelos e não depende de ocultação visual.

O campo de aptidão no candidato é calculado a partir de registros segregados; o modelo de saúde expõe os campos mínimos de nome, cargo e auditoria. Os templates de documentos excluem de início categorias antigas sensíveis ou sem justificativa atual. Isso segue minimização e privilégio mínimo como decisões de engenharia, sem substituir a validação jurídica, de RH, DP ou Saúde Ocupacional.

### 7.5 Testabilidade e verificabilidade

Os testes cobrem fluxos positivos e negativos: tentativas de escrita direta, aprovadores distintos, reabertura de solicitação após alteração material, nota/corte QAE, exigência de motivo condicional, bloqueio de gate, separação de acesso ocupacional, critérios gerados por perfil e pré-condições de treinamento/avaliação. O comando testado passa pelo runner da configuração da IDE e usa uma base local de teste. Os testes não substituem UAT, revisão de acessos, testes visuais de todas as views, validação de migração em cópia produtiva ou revisão do processo oficial.

## 8. Guia de instalação e atualização

### 8.1 Compatibilidade e preparação

Este addon é um módulo Python para **Odoo 20.0**. Instale `Recrutamento` (`hr_recruitment`); sua dependência direta carrega também os módulos necessários, incluindo RH. A implantação requer **Odoo.sh ou Odoo self-hosted/on-premise** com acesso aos arquivos e ao caminho de addons. Odoo Online não aceita addons customizados que contenham código Python. Não instale inicialmente em produção: use uma base de desenvolvimento/staging, backup testado e usuário administrador técnico.

### 8.2 Instalação na base local deste repositório

O caminho `addons/` do repositório já está no `addons_path` da configuração local `local-infra/.local/ide-odoo.conf`; a configuração da IDE usa `.idea/runConfigurations/Voigt_Odoo_IDE.xml`.

1. Inicie o PostgreSQL local utilizado pelo projeto e abra a configuração **Voigt Odoo Local (IDE Debug/Test)** no IDE. Para instalar em uma base de teste descartável nova, rode o runner com `--init`:

   ```bash
   set -a
   source local-infra/.local/ide-runner.env
   set +a
   PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
     --http-interface=127.0.0.1 --http-port=8070 \
     -d voigt_hr_recruitment_install_test \
     --init=voigt_hr_recruitment --stop-after-init
   ```

   Use um nome de banco que possa ser descartado. O parâmetro `--init` instala módulo e dependências; não o aponte para uma base de produção.

2. Para atualização de uma base em que o addon já está instalado, troque `--init` por `--update=voigt_hr_recruitment`. Faça backup/snapshot antes de qualquer atualização de base com dados.
3. Para rodar os testes Odoo nessa base de teste, use:

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

4. Para abrir a interface na base de teste, inicie o runner sem `--stop-after-init` e selecione a mesma base explicitamente:

   ```bash
   set -a
   source local-infra/.local/ide-runner.env
   set +a
   PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
     --http-interface=127.0.0.1 --http-port=8070 \
     -d voigt_hr_recruitment_install_test
   ```

   Acesse `http://127.0.0.1:8070`. Em produção/staging, o serviço Odoo é reiniciado pelo procedimento operacional da plataforma, não pelo runner de desenvolvimento.

### 8.3 Instalação self-hosted por linha de comando

1. Coloque `voigt_hr_recruitment/` em um diretório versionado de addons customizados (por exemplo, `/opt/odoo/custom-addons/voigt_hr_recruitment/`) e confira que a estrutura contém `__manifest__.py`, `__init__.py`, `models/`, `views/`, `data/`, `security/` e `tests/`.
2. Adicione o diretório raiz `/opt/odoo/custom-addons` ao `addons_path` da configuração da instância, mantenha o diretório padrão de addons e reinicie o serviço Odoo.
3. Na interface, habilite modo desenvolvedor, abra **Aplicativos > Atualizar lista de aplicativos > Atualizar**, remova o filtro **Aplicativos**/selecione **Extra**, busque **Voigt Recruitment Process** e clique em **Ativar**. A sequência da interface segue o procedimento oficial de instalação/atualização de módulos.
4. Alternativamente, em uma base de teste, use `odoo-bin -c <arquivo_conf> -d <base_teste> --init=voigt_hr_recruitment --stop-after-init`. Após colocar nova versão do código, atualize com `--update=voigt_hr_recruitment`; valide logs e testes antes de promover.

### 8.4 Odoo.sh e atualização pelo Apps

Inclua o diretório do addon em um repositório/branch conectado ao projeto Odoo.sh, publique primeiro em branch de desenvolvimento e instale pela interface **Apps** após atualizar a lista. Teste numa branch de staging antes da produção. Ao publicar alteração de módulo que exige atualização de dados/views, incremente a versão do manifesto conforme o processo da equipe e use o procedimento de upgrade da plataforma. Não foi executada implantação Odoo.sh nesta entrega.

Na tela **Apps**, a atualização usa o menu de ações do módulo e **Upgrade**. A desinstalação pode apagar registros do addon e módulos dependentes; faça snapshot e revise os efeitos antes de desinstalar. Esta implementação não declara scripts de migração para dados legados; testar explicitamente a atualização/desinstalação em cópia antes de qualquer mudança de produção.

## 9. Tutorial de configuração inicial

### 9.1 Usuários e permissões

Abra **Definições > Usuários e Empresas > Usuários** (ou, na página inicial de Definições, **Usuários > Gerenciar usuários**) e atribua os grupos conforme responsabilidade e aprovação da matriz de acesso. Nesta instância o aplicativo se chama **Definições**; “Configurações” é o nome da área/página, não o nome do aplicativo no seletor.

- **RH/Recrutador**: `Recruitment / User` (`hr_recruitment.group_hr_recruitment_user`), para operar o recrutamento e acessar menus do processo Voigt.
- **Responsável Voigt**: `Voigt Recruitment Manager`, que herda o papel de gerente de recrutamento e recebe funções de aprovação, templates, checklist, integração e decisão.
- **Saúde Ocupacional**: `Voigt Occupational Health` e acesso somente ao modelo de aptidão. Não atribuir `hr.applicant` apenas para consultar aptidão; o teste confirmou que esse grupo isolado não pode consultar candidatos.
- **Psicólogo organizacional**: `Voigt Organizational Psychologist` para campos/resumos de avaliação psicológica. A matriz de acesso a candidatos e a forma de execução da entrevista devem ser aprovadas em UAT; este grupo não substitui o acesso nativo de recrutamento, e o escopo de acesso não deve ser ampliado sem revisão de privacidade.

O addon não atribui automaticamente grupos a usuários de produção. Contas técnicas/testes não devem ser replicadas com senhas ou dados pessoais reais.

### 9.2 Estágios e perfis de vaga

1. Abra **Recrutamento > Configuração > Estágios** e edite os estágios existentes; o addon não cria um Kanban predefinido. Se **Estágios** não aparecer, habilite o modo desenvolvedor conforme a seção 10.2; nesta instância o menu nativo fica oculto sem esse modo.
2. Use `Job Specific`/Vagas para associar a etapa às posições correspondentes. Marque `Controle de passagem Voigt` conforme a tabela do tutorial de processo abaixo. Uma etapa com controle `Sem bloqueio Voigt` conserva o comportamento padrão.
3. Configure ao menos as fases necessárias ao processo real: abertura/triagem, RH, técnica, avaliações/entrevistas, documentação/aptidão, proposta e contratação. Use estágios comuns ou específicos a vagas conforme a organização existente; não duplique estágios sem decisão do RH.
4. Abra **Recrutamento > Vagas de emprego**, selecione a vaga (ou clique **Novo**) e defina `Perfil do processo Voigt`: Administrativo, Produção - Rebarbação, Produção - Moldagem, Mecânico de Manutenção ou Outro. Nesta instância, a tela inicial do aplicativo já é a lista/painel de vagas; **Configuração > Vagas de emprego** é apenas um título de grupo do menu, não o caminho para criar vagas. O perfil dirige os critérios técnicos e as etapas de onboarding específicas.
5. Revise os modelos em **Processo Voigt > Modelos do checklist**, **Critérios por perfil** e **Habilidades e atitudes RQ 006**. Desative ou edite itens que não sejam exigidos pela matriz/documentação aprovada. Templates iniciais são dados carregados na instalação, não cópia completa do RQ 052/TAB 01.

### 9.3 Etapas Voigt e pré-condições

| Controle no estágio | O que o sistema confere ao mover o candidato para a etapa |
|---|---|
| Sem bloqueio Voigt | Nenhuma regra adicional do addon. |
| Exige avaliação RH aprovada | Existe avaliação RH com resultado `Apto` ou `Liberado condicional`. |
| Exige entrevista técnica aprovada | Existe avaliação técnica com resultado `Apto` ou `Liberado condicional`. |
| Exige documentos e aptidão ocupacional | Todos os itens obrigatórios estão `Verificado` ou `Dispensado` com justificativa e o último resultado ocupacional é `Apto`. |
| Exige aprovação RQ 077, documentos e aptidão | RQ 077 associada à vaga está aprovada, checklist obrigatório completo e aptidão `Apto`. |

O bloqueio roda no servidor ao gravar `stage_id`. Não existe uma ordem rígida de estágios criada pelo addon: mapear a política do RH para os gates e testar cada caminho, inclusive rejeição/retorno. O corte QAE não é gate independente: o resultado fica na avaliação e a etapa RH/técnica exige avaliação do tipo correspondente.

## 10. Tutorial passo a passo do fluxo seletivo e admissional

Este roteiro foi organizado na ordem em que os registros precisam existir. Faça primeiro a configuração (uma vez por base); depois use o caso fictício abaixo para percorrer o fluxo de ponta a ponta.

**Como ler os caminhos:** clique no ícone de nove pontos (seletor de aplicativos) para abrir cada aplicativo. Os nomes abaixo correspondem à interface pt_BR observada na base Voigt (Odoo 20). O nome **Definições** identifica o aplicativo; **Configurações gerais** é uma seção dentro dele. “Vagas de emprego” é a tela inicial do aplicativo Recrutamento. Alguns menus técnicos, como **Estágios**, só aparecem com modo desenvolvedor ativado. A documentação oficial do Odoo também descreve a tela inicial de Recrutamento como o painel de vagas e explica que estágios podem ser associados a vagas específicas; a interface local foi conferida para registrar os rótulos exatos desta base. ([documentação Odoo: Recrutamento](https://www.odoo.com/documentation/20.0/applications/hr/recruitment.html))

> **Dados de treinamento:** o nome do candidato e os dados operacionais abaixo são fictícios. Não use dados reais de candidatos em uma base de demonstração. A faixa salarial é uma referência textual, pois os documentos consultados não definem um valor fixo vigente.

### 10.1 Preparar usuários e permissões

Para o teste completo, use o usuário **Administrator** do Odoo, que pertence a `base.group_system`. O XML do addon já atribui esse usuário ao grupo **Voigt Recruitment Manager**. Administradores de sistema podem aprovar uma solicitação própria nas duas etapas, fazer aprovação condicional da própria avaliação e registrar o resultado ocupacional, além de abrir o menu de aptidão. O nome do aprovador e o horário continuam gravados em cada decisão.

Essa exceção é para administração/teste: um usuário com `base.group_system` exerce privilégios amplos sobre o Odoo. No processo real, use pessoas distintas como requisitante, aprovador do setor, diretoria e Saúde Ocupacional, conforme a matriz aprovada. Usuários comuns continuam bloqueados de aprovar a própria solicitação e de registrar aptidão sem o grupo ocupacional.

- **Breadcrumb:** `Seletor de aplicativos (nove pontos) > Definições > Usuários e Empresas > Usuários > Administrator`.
- Alternativa: na página inicial de **Definições**, seção **Usuários**, clique **Gerenciar usuários** e abra **Administrator**. A documentação oficial descreve esse atalho pela seção Usuários e pelo link Gerenciar usuários. ([documentação Odoo: Usuários](https://www.odoo.com/documentation/20.0/applications/general/odoo_basics/users.html))
- Confira os grupos **Configurações / Administração** e **Recrutamento / Manager** (o nome pode aparecer como **Voigt Recruitment Manager**). O addon carrega esse último para o usuário administrador padrão.
- Para um usuário operacional distinto, atribua somente os grupos exigidos pelo papel: **Recruitment / User**, **Voigt Recruitment Manager**, **Voigt Occupational Health** ou **Voigt Organizational Psychologist**. Não atribua o grupo de saúde a recrutadores comuns.

### 10.2 Preparar departamento, cargo e etapas

**Departamento**

- **Breadcrumb:** `Seletor de aplicativos > Funcionários > Departamentos > Novo` (ou abra um departamento existente).
- Use um departamento existente da empresa, por exemplo **MACAHARIA** se esse for o departamento real exibido na base. Confirme que pertence à mesma empresa selecionada na solicitação. Se não existir, crie um departamento de teste vinculado à empresa Voigt. A aprovação do setor usa o gerente do departamento quando houver um gerente cadastrado.

**Cargo/vaga**

- **Breadcrumb:** `Seletor de aplicativos > Recrutamento > Vagas de emprego > Novo`.
- Ao abrir **Recrutamento**, esta instância mostra diretamente o painel/lista **Vagas de emprego**; use o botão **Novo** no alto à esquerda. A documentação oficial confirma que o painel principal de Recrutamento lista as posições. Não procure por **Cargos** em Configuração: esse não é o rótulo nem o caminho desta versão/interface.
- Após aprovar a RQ 077 no passo seguinte, crie a vaga **Auxiliar de Produção - Rebarbação (Treinamento)**, associe o departamento da requisição, escolha o perfil **Auxiliar de Produção - Rebarbação**, vincule a **Solicitação RQ 077** aprovada e informe uma vaga. Para demonstrar Moldagem, use outro cargo e o perfil correspondente; não misture os dois perfis.

**Estágios**

- **Breadcrumb:** `Seletor de aplicativos > Definições > Configurações gerais > Ferramentas de desenvolvimento > Ativar o modo de desenvolvedor`.
- Passo a passo: abra o seletor de aplicativos (nove pontos), entre em **Definições**, abra **Configurações gerais**, role até **Ferramentas de desenvolvimento** e clique **Ativar o modo de desenvolvedor**. Volte ao seletor, abra **Recrutamento > Configuração > Estágios**. Depois de concluir a configuração, abra o ícone de ferramentas do desenvolvedor (bug) e selecione **Sair do modo de depuração**, se não precisar mais dele.
- Por que este passo existe: na base examinada, **Estágios** é um menu técnico nativo que não fica visível no modo normal. O item **Vagas de emprego** mostrado como título no menu **Configuração** também não é um atalho para a lista de vagas.
- Edite os estágios existentes e use o campo **Controle de passagem Voigt**. Associe as etapas às vagas Voigt pelo campo de vagas específicas quando necessário. Não crie um estágio por nome se já existir equivalente.
- Configure a sequência de teste: uma etapa inicial sem bloqueio; etapa **Entrevista RH** com `Exige avaliação RH aprovada`; etapa **Entrevista técnica** com `Exige entrevista técnica aprovada`; etapa **Admissão/documentos** com `Exige documentos e aptidão ocupacional`; etapa **Proposta** com `Exige aprovação RQ 077, documentos e aptidão ocupacional`; etapa **Contratado** marcada com o campo nativo **Hired Stage/Etapa contratada**. A etapa contratada pode ficar sem gate; a etapa Proposta deve aplicar o gate final.
- Os nomes acima são exemplos. Configure o campo no estágio que realmente corresponde à fase da empresa. A validação é feita ao alterar a candidatura para a etapa.

### 10.3 Conjunto de dados fictício para o tutorial

| Campo | Valor para digitar no ambiente de teste |
|---|---|
| Empresa | METALURGICA VOIGT LTDA (ou a empresa Voigt selecionada na base) |
| Departamento | MACAHARIA, se existir e for a área da vaga; caso contrário, o departamento de teste vinculado à empresa |
| Cargo solicitado | Auxiliar de Produção - Rebarbação (use a descrição que corresponde ao cargo real solicitado) |
| Quantidade | 1 |
| Tipo de contratação | Efetivo |
| Motivo | Aumento do quadro |
| Justificativa | `Caso fictício de treinamento: demonstrar o fluxo de requisição e admissão para a posição de Auxiliar de Produção - Rebarbação. Validar demanda e faixa com a liderança antes de qualquer uso real.` |
| Jornada | `Turno conforme escala aprovada do departamento (dado de demonstração)` |
| Referência salarial | `Faixa salarial vigente aprovada para a vaga (preencher após validação)` |
| Substituição | Deixar vazio, pois o motivo escolhido é aumento do quadro |
| Requisitante | Administrator (usuário conectado) |
| Candidato (nome para o exercício) | `Camila Andrade - Candidata Fictícia Voigt` |
| E-mail para o exercício | `camila.andrade.treinamento@example.invalid` (endereço de teste não roteável; não envie mensagens) |
| Telefone, CPF, endereço e currículo | Deixe vazios neste exercício; use somente dados reais fornecidos pelo candidato em processos autorizados. Não invente CPF nem use dados de uma pessoa real no banco de demonstração. |
| Recrutador da candidatura | Usuário responsável conectado; confirme que a vaga preencheu o valor padrão correto |
| Avaliação RH | Resultado Apto; parecer de treinamento sem dados pessoais |
| Avaliação técnica | Perfil Rebarbação; critérios do template aplicável, evidência fictícia e resultado Apto |
| QAE (se aplicável) | Use somente se a faixa escolaridade e revisão do questionário estiverem confirmadas; exemplo aritmético: 70/100, corte 60/100, revisão RQ 079 ou RQ 081 correspondente |
| Documentos | CPF, Documento oficial de identificação e Comprovante de endereço: Recebido e depois Verificado. São itens fictícios de checklist; não anexe documentos reais neste cenário. |
| Aptidão | Registrar resultado Apto somente como decisão de demonstração; nunca digitar diagnóstico, exame ou nota clínica |
| Treinamento RQ 006 | Treinamentos gerais e requisitos do posto marcados como concluídos apenas no cenário de simulação |

**Escolha da vaga para associar à RQ:** no painel da base espelhada podem existir vagas como **AUX. DE PRODUÇÃO** e **AUX. DE PRODUÇÃO** vinculadas a departamentos diferentes ou com configuração própria. O nome parecido sozinho não prova que a vaga serve para a requisição. Antes de seguir, compare cargo solicitado, empresa, departamento, perfil Voigt e situação/quantidade da vaga. Use uma vaga existente se esses dados forem compatíveis com a RQ aprovada; se nenhuma corresponder, siga o caminho de nova vaga em 10.6.2. No exemplo de MACAHARIA, a vaga **AUX. DE PRODUÇÃO** pode ser reaproveitada somente se RH confirmar que ela representa a posição de Rebarbação solicitada. Caso contrário, use o caminho de criação. Este tutorial usa uma vaga para a RQ fictícia; uma requisição aprovada pode estar vinculada a mais de uma posição, se o escopo aprovado assim exigir. Cada posição, porém, pode apontar para apenas uma RQ.

### 10.4 Passo 1 - criar e salvar a requisição RQ 077

- **Breadcrumb:** `Seletor de aplicativos > Recrutamento > Processo Voigt > Solicitações RQ 077 > Novo`. A página de destino pode ter o título **Solicitações de admissão**; é o mesmo menu de requisições RQ 077.
- Preencha os valores da tabela anterior nos campos **Empresa**, **Departamento**, **Cargo solicitado**, **Quantidade**, **Tipo de contratação**, **Motivo**, **Justificativa**, **Jornada de trabalho** e **Referência salarial**. Mantenha **Substituição** vazio para o motivo Aumento do quadro. O campo **Solicitante** vem preenchido com o usuário conectado.
- Clique no ícone **Salvar** (nuvem/seta no formulário) ou use `Ctrl+S`. A solicitação deve ser gravada com um identificador `RQ ...` e status **Rascunho**. Agora o formulário aceita o estado inicial rascunho enviado pelo cliente Odoo. Se aparecer a validação anterior “Novas solicitações devem começar em rascunho...”, atualize o módulo para a versão corrigida (`--update=voigt_hr_recruitment`) e recarregue a página.
- Clique **Enviar para aprovação**. O status passa para **Aguardando aprovação do setor**. Não tente preencher os campos de aprovação manualmente; eles são de auditoria e somente as ações devem gravá-los.

### 10.5 Passo 2 - aprovar setor e diretoria com Administrator

**Aprovar o setor**

- **Breadcrumb:** `Recrutamento > Processo Voigt > Solicitações RQ 077 > abrir RQ ... > Aprovar setor`
- Com **Administrator**, clique **Aprovar setor**. O status deve mudar para **Aguardando diretoria**; confira **Aprovador do setor** e **Aprovação do setor em** preenchidos.

**Aprovar diretoria**

- **Breadcrumb:** `Recrutamento > Processo Voigt > Solicitações RQ 077 > abrir a mesma RQ ... > Aprovar diretoria`
- Com o mesmo **Administrator**, clique **Aprovar diretoria**. O status esperado é **Aprovada**; confira usuário e data nos campos de aprovação. Esse caminho com um único administrador é aceito para percorrer o fluxo de teste. Em produção, use aprovadores distintos e o processo de autoridade da empresa.

Se o usuário não for administrador do sistema, ele não pode aprovar a própria requisição nem aprovar as duas etapas como a mesma pessoa. Associe um gestor ao departamento para a aprovação setorial ou use o fluxo de usuários designados.

### 10.6 Passo 3 - associar a RQ 077 a uma vaga

O painel **Vagas de emprego** mostra as posições cadastradas. O botão **Configurar** em cada cartão abre essa vaga para edição; **Novo** cria outra posição. O Odoo permite editar uma posição existente ou criar uma nova a partir desse painel ([documentação oficial de Cargos](https://www.odoo.com/documentation/20.0/pt_BR/applications/hr/recruitment/new_job.html)). Para a vaga deste exemplo, siga um dos caminhos abaixo. Não crie uma vaga duplicada só para conseguir associar a solicitação. Se a RQ aprovada cobrir mais de uma posição, repita a associação para cada vaga compatível.

#### 10.6.1 Caminho A - reaproveitar vaga existente

Use este caminho quando já existir uma vaga com empresa, departamento e perfil compatíveis com a RQ 077 aprovada. A vaga mostrada na captura como **AUX. DE PRODUÇÃO** é um exemplo a conferir, não uma escolha automática.

1. **Breadcrumb:** `Seletor de aplicativos > Recrutamento > Vagas de emprego`.
2. Se necessário, limpe os filtros de empresa/departamento ou use a busca no topo para localizar a vaga pelo nome. A captura mostra o filtro **MACAHARIA** aplicado e somente `1-2 / 2`; portanto, ela não representa todas as vagas da base. Clique em **Tudo** na seção Departamento para ampliar os resultados, ou ajuste a busca.
3. Na linha/cartão da posição apropriada, clique **Configurar**. Não clique em **Novo** neste caminho.
4. Confira o nome, a empresa e o departamento. Defina **Perfil do processo Voigt** de acordo com a atividade real: **Auxiliar de Produção - Rebarbação** somente para uma posição de Rebarbação; use Moldagem, Mecânico ou Administrativo apenas quando corresponderem ao trabalho solicitado.
5. No campo **Solicitação RQ 077**, selecione a RQ `RQ ...` aprovada. Confira que ela corresponde à mesma empresa/departamento e ao cargo. Salve.
6. Se a posição já estiver associada a outra requisição, pare e confirme com RH qual solicitação deve ser vinculada. O campo do addon armazena uma requisição por vaga; não substitua um vínculo existente sem autorização e sem avaliar o histórico. A quantidade aprovada na RQ também não atualiza automaticamente a quantidade de recrutamento da vaga: confira a capacidade e ajuste-a somente com aprovação de RH.
7. Associe a vaga às etapas Voigt preparadas em 10.2, se a configuração por vaga específica for usada.

#### 10.6.2 Caminho B - criar uma nova vaga

Use este caminho somente se a posição necessária ainda não existir ou se RH confirmou que a vaga existente não representa o cargo/departamento/perfil da RQ.

1. **Breadcrumb:** `Seletor de aplicativos > Recrutamento > Vagas de emprego > Novo`.
2. Informe **Auxiliar de Produção - Rebarbação (Treinamento)**, empresa Voigt, departamento aprovado na RQ e responsável de recrutamento. Configure o número de vagas conforme a quantidade aprovada e validada por RH; para este exemplo, use `1`.
3. Defina **Perfil do processo Voigt = Auxiliar de Produção - Rebarbação**. O nome e o perfil devem representar o trabalho real e a RQ; não use o perfil de Rebarbação para uma vaga de Moldagem.
4. No campo **Solicitação RQ 077**, selecione a RQ `RQ ...` em estado **Aprovada**. Salve a vaga. O addon não cria posições automaticamente: essa conferência é deliberada para RH validar cargo, departamento, empresa e quantidade.
5. Associe a vaga às etapas Voigt preparadas em 10.2, se a configuração por vaga específica for usada.

Em ambos os caminhos, retorne à lista e confirme que a vaga aparece com o departamento/empresa esperados. Depois continue para 10.7. Se o campo **Solicitação RQ 077** não estiver visível, abra o formulário por **Configurar** ou **Novo** (não permaneça apenas no cartão do painel) e confirme que o addon está atualizado e instalado.

### 10.7 Passo 4 - criar candidatura e confirmar checklist inicial

- O trabalho cotidiano normalmente começa com o recrutador registrando a candidatura e escolhendo a vaga aprovada. O Odoo permite criar uma candidatura pela vaga ou pela lista geral; ao partir da vaga, o cargo e o recrutador podem vir preenchidos automaticamente ([documentação oficial: adicionar candidatos](https://www.odoo.com/documentation/20.0/pt_BR/applications/hr/recruitment/add_applicants.html)).

**Criar uma candidatura nova para a vaga deste processo**

1. **Breadcrumb recomendado:** `Seletor de aplicativos > Recrutamento > Vagas de emprego > abrir a vaga da RQ aprovada > Novo` (na tela da vaga, **Novo** cria candidatura para essa posição).
2. Se estiver na lista geral como na captura: `Seletor de aplicativos > Recrutamento > Candidaturas > Todas as candidaturas > Novo`. O menu **Candidaturas** abre opções como **Por vagas**, **Por grupos de talentos** e **Todas as candidaturas**. Nesta rota, escolha explicitamente no campo **Cargo/Vaga** a vaga associada à RQ que acabou de aprovar; não deixe o cargo vazio nem selecione uma posição apenas por ter nome parecido.
3. Preencha **Candidato** com `Camila Andrade - Candidata Fictícia Voigt`, **E-mail** com `camila.andrade.treinamento@example.invalid` apenas para demonstração e **Recrutador** com a pessoa que conduzirá a seleção. O e-mail `.invalid` é fictício e não deve receber mensagens. Deixe telefone, LinkedIn e currículo vazios para o exercício. Na operação real, o recrutador registra somente dados recebidos diretamente do candidato e permitidos pela política da empresa.
4. Confira **Cargo/Vaga**, **Empresa** e **Departamento**. Empresa/departamento podem ser preenchidos a partir da vaga; corrija somente se a RQ aprovada e a posição confirmarem outro valor. Mantenha a etapa inicial padrão **Novo** (ou o estágio inicial já configurado pela empresa) e clique em **Salvar**. Não avance a candidatura antes de executar as avaliações e completar os gates correspondentes.
5. Abra a candidatura recém-criada, confira seu nome e cargo e abra a aba **Processo Voigt**. O addon gera para cada nova candidatura os itens ativos do checklist que sejam globais (`all`) ou correspondam ao perfil da vaga: neste exemplo, **CPF**, **Documento oficial de identificação** e **Comprovante de endereço** são obrigatórios; comprovante de escolaridade é opcional. A qualificação técnica adicional aplica-se ao perfil Mecânico.

**Quando o nome já aparece entre as candidaturas existentes (como as 628 linhas da captura)**

1. Na lista **Todas as candidaturas**, use a busca para procurar a pessoa antes de criar. Abra o registro e confira **Cargo/Vaga**, etapa e situação. A lista pode conter histórico de processos diferentes; o nome da pessoa, por si só, não indica que o registro pertence à vaga/RQ atual.
2. Se houver candidatura ativa para esta mesma vaga e este mesmo processo, abra-a e continue o registro existente. Não crie outra candidatura duplicada para a mesma pessoa, vaga e processo.
3. Se o registro encontrado for de uma vaga ou seleção antiga, não o mova para a nova vaga nem reutilize sua aba **Processo Voigt**: avaliações, documentos e histórico pertencem àquela candidatura. Após confirmar que a nova RQ/posição foi aprovada e que a pessoa pode participar deste processo, crie uma candidatura nova pelo passo anterior, selecione a vaga atual e use os dados atualizados que o próprio candidato fornecer. Assim, a nova candidatura terá sua própria etapa, checklist e avaliações; a antiga permanece como histórico.
4. Se houver mais de um registro ativo para a mesma pessoa e vaga, interrompa o cadastro e peça ao responsável de RH para identificar o registro correto. Não recuse, arquive, mescle nem apague duplicidades durante este tutorial.

O usuário com papel **Recrutamento / User** pode cadastrar candidaturas conforme seus acessos. A aba **Processo Voigt** é restrita ao grupo **Voigt Recruitment Manager**; portanto, no exercício ponta a ponta, use Administrator (configurado para o tutorial) ou peça a um Voigt Manager para executar os passos Voigt. A documentação oficial descreve o cadastro manual de candidatura na vaga e a lista de todas as candidaturas como caminhos nativos do Odoo ([Adicionar candidatos](https://www.odoo.com/documentation/20.0/pt_BR/applications/hr/recruitment/add_applicants.html), [lista de candidaturas recusadas/todas](https://www.odoo.com/documentation/20.0/applications/hr/recruitment/refuse_applicant.html)).

- Se a aba **Processo Voigt** não aparecer, confira que o usuário conectado tem **Voigt Recruitment Manager**; a aba é restrita por grupo.

### 10.8 Passo 5 - registrar e aprovar avaliações

**Avaliação de RH**

- **Breadcrumb:** `Recrutamento > Candidaturas > abrir Camila Andrade - Candidata Fictícia Voigt > Processo Voigt > Avaliações`
- Adicione linha e escolha **Entrevista RH**; preencha **Avaliador**, **Data da avaliação**, **Revisão** (ex.: `PO 017 Rev. B - roteiro de treinamento`) e parecer fictício em **Parecer**. Salve a linha, abra a avaliação se necessário e clique **Marcar apto**.
- Mova a candidatura para a etapa **Entrevista RH** configurada com gate. A alteração deve ser aceita. Se tentar antes de marcar Apto, o Odoo deve bloquear a mudança.

**Avaliação técnica**

- No mesmo caminho, adicione avaliação **Entrevista técnica**, com avaliador, data e revisão/roteiro aplicável. Ao salvar, devem aparecer critérios técnicos do perfil Rebarbação. Preencha o resultado e uma evidência curta de treinamento para cada critério, abra o formulário da avaliação e clique **Marcar apto**.
- Mova a candidatura para a etapa **Entrevista técnica**. Ela só deve aceitar a candidatura depois que a avaliação técnica estiver aprovada.

**QAE opcional**

- Só crie uma avaliação **QAE 01 / RQ 079** ou **QAE 02 / RQ 081** quando esse questionário for aplicável à pessoa e à revisão oficial vigente. Preencha a pontuação total observada, o máximo `100`, o corte da revisão confirmada (o template documentado usa `60`) e clique **Calcular resultado**. O sistema calcula a comparação numérica; não corrige questionário nem escolhe qual versão aplicar.
- Para **Aprovação condicional**, informe a justificativa da decisão. Administrator pode aprovar a própria avaliação para o cenário demonstrativo; avaliadores comuns continuam sujeitos à separação de funções.

### 10.9 Passo 6 - completar RQ 052 e registrar aptidão

**Checklist**

- **Breadcrumb:** `Recrutamento > Candidaturas > abrir Camila Andrade - Candidata Fictícia Voigt > Processo Voigt > Checklist de admissão`
- Para **CPF**, **Documento oficial de identificação** e **Comprovante de endereço**, altere o campo **Estado** de Não solicitado para **Recebido** e salve. Em seguida, em cada linha, clique **Verificar**. Confira **Verificado por** e **Verificado em** preenchidos. Não precisa anexar evidências reais para este exercício.
- Se um documento obrigatório realmente não se aplicar, somente um Voigt Manager deve usar **Dispensar** após informar motivo. Não dispense itens apenas para passar no tutorial.

**Aptidão ocupacional**

- No bloco **Aptidão ocupacional** da aba, clique **Solicitar avaliação**.
- **Breadcrumb:** `Recrutamento > Processo Voigt > Avaliações de aptidão > abrir avaliação pendente > Registrar apto`
- Com Administrator de sistema, clique **Registrar apto** para validar o caminho de demonstração. O status muda para **Apto**, com usuário e horário. Um profissional de Saúde Ocupacional usa o mesmo fluxo com seu grupo próprio na operação real.
- Não inclua exame, diagnóstico, laudo ou informação clínica em nenhum campo, nome do registro ou chatter.
- Retorne à candidatura e mova para **Admissão/documentos**. O gate precisa ver checklist obrigatório completo e aptidão Apto. Depois mova para **Proposta**; o gate final também confere a RQ 077 aprovada associada à vaga.

### 10.10 Passo 7 - contratar e abrir Integração RQ 006

- **Breadcrumb:** `Recrutamento > Candidaturas > abrir candidatura > Etapa Contratado`
- Mova a candidatura para o estágio nativo **Contratado** marcado como **Hired Stage**. O Odoo cria/vincula o empregado conforme o fluxo nativo; o addon cria um único registro de integração ligado à candidatura. Se esse vínculo não for produzido pela configuração nativa da base, finalize a contratação de RH conforme a prática local antes de prosseguir.
- **Breadcrumb:** `Recrutamento > Processo Voigt > Integração RQ 006 > abrir a integração do candidato`
- Confira **Data de admissão**, perfil e datas padrão de avaliação (15 e 30 dias depois). Datas são editáveis; PO 017 e RQ 006 divergem sobre o primeiro prazo e a empresa deve decidir qual vale para produção.

### 10.11 Passo 8 - concluir treinamentos, liberação PRÁTICO e avaliação

No exemplo de Rebarbação, o perfil deve exibir **Área de produção = Acabamento / Rebarbação**, preenchida pelo sistema. Não troque para Moldagem.

- Na integração, marque **Treinamento de RH**, **Treinamento da Qualidade**, **Treinamento de Segurança** e **Treinamento operacional** somente para simular que foram realizados. Selecione um **Líder ou Anjo da Guarda** existente; se a base de treinamento não tiver, crie previamente um empregado fictício em `Funcionários > Funcionários` sem dados pessoais reais.
- Marque **Fichas técnicas e especificações repassadas**, **Tarefa específica do setor repassada sob supervisão** e **EPIs do posto e treinamento de uso conferidos**. Esses campos espelham requisitos gerais do RQ 006 e específicos de produção identificados nos documentos de admissão e descrição da vaga.
- Clique **Aprovar liberação PRÁTICO**. A auditoria deve mostrar **Aprovado por** e **Aprovado em**. Para Mecânico, use o perfil Mecânico e marque **Equipamentos e rotinas de manutenção aplicáveis repassados**; os campos de produção não se aplicam.
- Na lista **Habilidades e atitudes RQ 006**, preencha as nove habilidades e dez atitudes. Para apenas demonstrar o salvamento, use nota fictícia `3 - Bom` em cada linha e registre notas de treinamento; não considere essa nota avaliação de pessoa real.
- Clique **Efetivar** para encerrar o exercício. Para treinar alternativas, crie outra candidatura fictícia e use **Acompanhar / adequar** ou **Encerrar**. A ação exige que todas as 19 linhas estejam avaliadas e grava usuário/data.

### 10.12 Resultado esperado e solução de problemas

Ao final, deve existir uma requisição **Aprovada**, vaga associada à requisição, candidatura no estágio **Contratado**, checklist obrigatório concluído, aptidão resumida como Apto e uma integração RQ 006 com PRÁTICO liberado e decisão final auditada.

- **Erro ao salvar a nova requisição:** instale o upgrade de `voigt_hr_recruitment`, atualize a tela e tente de novo. A correção permite `state='draft'` e valores vazios nos campos de aprovação; continua rejeitando estados iniciais diferentes de Rascunho e dados de aprovação não vazios.
- **Aprovar setor/diretoria desabilitado ou erro de autop aprovação:** confira que a solicitação foi salva e enviada; o usuário de teste precisa ser membro de `base.group_system`. Para usuários regulares, use requisitante, gestor do setor e diretor diferentes.
- **Aba Processo Voigt ausente:** confirme o grupo **Voigt Recruitment Manager** e recarregue a candidatura.
- **Não consegue passar de etapa:** confira o gate atribuído ao estágio, resultado da avaliação apropriada, itens obrigatórios verificados/dispensados, resultado ocupacional Apto e associação da vaga à RQ 077 aprovada para a etapa Proposta.
- **Integração não criada:** confirme que a etapa para a qual moveu a candidatura tem a caixa nativa **Hired Stage** marcada; a integração não é criada simplesmente ao entrar em uma etapa com nome “Contratado”.
- **Não vê o menu Avaliações de aptidão:** entre como Administrator de sistema (base.group_system) ou atribua o grupo **Voigt Occupational Health** ao usuário de saúde designado.

## 11. Referências operacionais e pontos de conferência

Antes de cada implantação/uso real, conferir: versão Odoo 20.0; dependência `hr_recruitment`; versão vigente da PO/RQs e TAB 01; disponibilidade de perfis e templates atuais; grupos de usuário; etapa `Hired Stage`; gates da etapa; ligação da vaga à RQ; e backup do banco. Em dúvidas, prevalece a política corporativa aprovada, não a configuração inicial dos templates.

Este guia descreve o comportamento da versão implementada. A instalação foi exercitada na instância local e banco de teste do repositório, não em Odoo.sh ou produção. O relatório e o código permanecem sem commit, para revisão do solicitante.

## 12. Pontos para validação antes do piloto

1. Confirmar que PO 017 Rev. B, RQ 006/052/077/079/081 Rev. A/B ainda são os documentos vigentes e resolver o prazo divergente de avaliação inicial.
2. Obter a TAB 01 vigente e mapear requisitos/evidências por cargo. Ela não foi embutida como regra porque não foi localizada como fonte aprovada atual no conjunto analisado.
3. RH/DP deve revisar e completar o checklist RQ 052; os templates iniciais são intencionalmente mínimos.
4. Segurança/medicina do trabalho deve validar quem recebe o grupo de aptidão, os dados mínimos expostos nesse modelo restrito e a conclusão ocupacional necessária.
5. Definir os estágios reais por vaga e associar as travas adequadas usando `job_ids`; a instalação não cria estágios genéricos que poderiam alterar o Kanban existente.
6. Validar os critérios do Mecânico e os perfis de Rebarbação/Moldagem com os gestores das áreas. Nenhuma regra clínica, física ou de aparência foi automatizada.
7. Fazer UAT com usuários reais, matriz de acesso aprovada, política de retenção e base sintética. Os testes locais não são aceite operacional nem confirmação de conformidade legal.

O addon permanece sem commit, conforme solicitado.
