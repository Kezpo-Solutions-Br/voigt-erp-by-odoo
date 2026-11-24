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

`voigt.recruitment.request` armazena os dados essenciais da solicitação, número sequencial, empresa, departamento, cargo, motivo, modalidade, justificativa, quantidade, horário e referência salarial. As ações registram separadamente a aprovação do responsável pelo setor e da diretoria com usuário e horário. O requisitante não pode aprovar a própria solicitação, o mesmo usuário não pode realizar as duas aprovações e, quando o departamento possui gestor cadastrado, a aprovação do setor deve ser feita por esse gestor ou pelo grupo funcional Voigt autorizado.

Depois de aprovada, uma alteração material retorna a solicitação para rascunho e limpa as aprovações anteriores. A vaga nativa referencia a RQ 077 aprovada. A criação da vaga continua sendo uma ação do usuário, pois o documento não especifica defaults suficientes para gerar automaticamente todos os campos de uma posição.

### 3.3 Perfil de vaga e avaliação

`hr.job.voigt_profile` diferencia Administrativo, Produção - Rebarbação, Produção - Moldagem, Mecânico de Manutenção e Outro. Para avaliação técnica, critérios do perfil mecânico são gerados de templates com os tópicos observados no roteiro da função. Os critérios de produção distinguem Rebarbação e Moldagem. A experiência prévia com lixadeira está marcada como diferencial, não eliminatório, conforme a descrição da vaga.

As avaliações RH, técnica, diretoria, QAE 01/02, avaliação organizacional e experiência ficam em `voigt.applicant.assessment`. QAE 01 e QAE 02 recebem a revisão Rev. B e corte inicial 60/100. O total é registrado pelo avaliador: o addon não tenta corrigir automaticamente respostas abertas ou interpretar a qualidade de respostas discursivas. Recalcular uma nota após edição a devolve a pendente. A liberação condicional exige motivo, usuário aprovador distinto do avaliador e grupo Voigt autorizado.

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
- `__manifest__.py`: dependência, versão, arquivos carregados e licença.
- `models/voigt_recruitment_request.py`: RQ 077, etapas de aprovação, histórico e reabertura após alteração material.
- `models/voigt_applicant_assessment.py` e `models/voigt_applicant_assessment_criterion.py`: avaliações, QAE, decisões autorizadas e critérios por posição.
- `models/voigt_applicant_document.py` e `models/voigt_applicant_document_template.py`: checklist, evidências, verificação e dispensa com justificativa.
- `models/voigt_onboarding.py`, `models/voigt_onboarding_skill.py` e `models/voigt_onboarding_skill_template.py`: RQ 006, treinamento, critérios, liberação prática e decisão final.
- `models/hr_job.py`, `models/hr_recruitment_stage.py` e `models/hr_applicant.py`: extensões e travas de transição do recrutamento nativo.
- `data/recruitment_data.xml` e `data/recruitment_templates.xml`: sequência RQ 077 e templates iniciais baseados nos documentos.
- `security/`: grupo funcional, permissão mínima por modelo e domínios por empresa.
- `views/`: formulários, listas e menus do processo, campos na vaga/candidato/etapa e templates editáveis.
- `tests/test_voigt_recruitment.py`: testes de regras de fluxo e validações.

## 5. Testes e execução local

Os testes usam `BaseCommon` do Odoo, ficam importados em `tests/__init__.py` e são executáveis pela infraestrutura `TransactionCase` do Odoo. Foram exercitados:

- criação e aprovação em duas etapas da solicitação, mudança que exige aprovação nova e bloqueio de alteração direta do estado;
- campos obrigatórios da substituição;
- travas de etapa por avaliação e aptidão, criação automática do checklist e bloqueio de escrita direta no resultado ocupacional;
- cálculo do corte QAE 01, atualização da nota e liberação condicional;
- critérios técnicos gerados para Mecânico;
- recusa de liberação PRÁTICO sem os treinamentos e requisitos do posto;
- checklist de habilidades/atitudes RQ 006 e conclusão da decisão final.

Comando usado na base local temporária, passando pelo runner da configuração `.idea/runConfigurations/Voigt_Odoo_IDE.xml`:

```bash
set -a
source local-infra/.local/ide-runner.env
set +a
PYTHONPATH="$PWD" ./.venv/bin/python local-infra/ide-runner/odoo_ide_runner.py \
  --http-interface=127.0.0.1 --http-port=8070 \
  -d voigt_hr_recruitment_test2 \
  --update=voigt_hr_recruitment \
  --test-enable --test-tags /voigt_hr_recruitment --stop-after-init
```

**Resultado final:** 10 testes do módulo executados; `0 failed, 0 error`. O teste de aptidão também confirmou que o usuário de saúde não pode consultar `hr.applicant` e ainda consegue registrar a aptidão por meio do modelo restrito. Também passaram a compilação Python e a leitura sintática de todos os XML do addon. A inicialização/atualização carregou as views, ACLs, templates e modelos no Odoo 20.0. A aplicação iniciou pelo runner IDE e `GET /web/login` respondeu HTTP 200. A execução do runner exigiu fornecer `PYTHONPATH` e carregar `ide-runner.env` no shell; isso não altera a configuração salva da IDE.

Os avisos de `pdfminer.six` e `markdown2` ausentes vêm do ambiente de desenvolvimento e não impediram a instalação nem os testes do addon. Não foi feita validação visual interativa de cada view no navegador.

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
- [Odoo 20 - ORM e herança](https://www.odoo.com/documentation/20.0/developer/reference/backend/orm.html): modelos/recordsets, extensão por `_inherit`, constraints, `Command`, operações em lote e cache.
- [Odoo 20 - segurança](https://www.odoo.com/documentation/20.0/developer/reference/backend/security.html) e [tutorial para restringir acesso a dados](https://www.odoo.com/documentation/20.0/developer/tutorials/restrict_data_access.html): grupos, ACLs, regras, acesso a campos e validação no servidor.
- [Odoo 20 - arquivos de dados XML](https://www.odoo.com/documentation/20.0/developer/reference/backend/data.html) e [views](https://www.odoo.com/documentation/20.0/developer/reference/user_interface/view_records.html): carga ordenada de dados, menus, ações e herança de views.
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

ACLs, grupos e restrição por empresa foram declarados em `security/`. O grupo de recrutamento Voigt Manager herda o administrador nativo de recrutamento; o grupo ocupacional tem somente leitura/edição no modelo de aptidão, sem ACL de criação nem de `hr.applicant`; o recrutamento autorizado cria solicitações e o resultado só é gravado por ações restritas. Parecer psicológico e campos de gestão têm controle por grupos. A limitação de campo com `groups` é reforçada por ACLs/modelos e não depende de ocultação visual.

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

Em **Configurações > Usuários**, atribua os grupos conforme responsabilidade e aprovação da matriz de acesso:

- **RH/Recrutador**: `Recruitment / User` (`hr_recruitment.group_hr_recruitment_user`), para operar o recrutamento e acessar menus do processo Voigt.
- **Responsável Voigt**: `Voigt Recruitment Manager`, que herda o papel de gerente de recrutamento e recebe funções de aprovação, templates, checklist, integração e decisão.
- **Saúde Ocupacional**: `Voigt Occupational Health` e acesso somente ao modelo de aptidão. Não atribuir `hr.applicant` apenas para consultar aptidão; o teste confirmou que esse grupo isolado não pode consultar candidatos.
- **Psicólogo organizacional**: `Voigt Organizational Psychologist` para campos/resumos de avaliação psicológica. A matriz de acesso a candidatos e a forma de execução da entrevista devem ser aprovadas em UAT; este grupo não substitui o acesso nativo de recrutamento, e o escopo de acesso não deve ser ampliado sem revisão de privacidade.

O addon não atribui automaticamente grupos a usuários de produção. Contas técnicas/testes não devem ser replicadas com senhas ou dados pessoais reais.

### 9.2 Estágios e perfis de vaga

1. Abra **Recrutamento > Configuração > Estágios** (nome pode variar com menu/idioma) e edite os estágios existentes; o addon não cria um Kanban predefinido.
2. Use `Job Specific`/Vagas para associar a etapa às posições correspondentes. Marque `Controle de passagem Voigt` conforme a tabela do tutorial de processo abaixo. Uma etapa com controle `Sem bloqueio Voigt` conserva o comportamento padrão.
3. Configure ao menos as fases necessárias ao processo real: abertura/triagem, RH, técnica, avaliações/entrevistas, documentação/aptidão, proposta e contratação. Use estágios comuns ou específicos a vagas conforme a organização existente; não duplique estágios sem decisão do RH.
4. Em **Recrutamento > Configuração > Cargos** (ou abra a vaga), defina `Perfil do processo Voigt`: Administrativo, Produção - Rebarbação, Produção - Moldagem, Mecânico de Manutenção ou Outro. O perfil dirige os critérios técnicos e as etapas de onboarding específicas.
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

## 10. Tutorial operacional do processo seletivo e admissional

### Etapa 1 - registrar e aprovar necessidade (RQ 077)

1. Acesse **Recrutamento > Processo Voigt > Solicitações RQ 077** e crie um registro.
2. Preencha empresa, departamento, cargo, quantidade (mínimo 1), tipo de contratação (efetivo, temporário ou estagiário), motivo (aumento, substituição ou outros), justificativa, jornada e referência salarial.
3. Para motivo substituição, preencha a pessoa/cargo substituído. A regra valida essa informação.
4. Clique **Enviar para aprovação**. O responsável do departamento usa **Aprovar setor**; ele não pode aprovar se for o próprio requisitante. Se o departamento tem gestor cadastrado, esse gestor ou usuário Voigt Manager aprovado pela regra deve aprovar.
5. Outro usuário, diferente do solicitante e do aprovador do setor, usa **Aprovar diretoria**. A aprovação grava usuário e horário. Para rejeitar, preencha justificativa e use **Rejeitar**. Alteração material em RQ aprovada volta para rascunho e requer nova aprovação.

### Etapa 2 - criar e configurar a vaga

Depois de aprovada a RQ, crie a vaga no Recrutamento e relacione o campo `Solicitação RQ 077` à solicitação aprovada. Preencha título, departamento, empresa, quantidade, responsável, descrição, jornada e demais campos nativos. Selecione o perfil Voigt adequado. A vaga não é criada automaticamente a partir da requisição; o usuário confere os dados e cria o registro nativo, preservando o controle da publicação.

### Etapa 3 - registrar candidato e avaliações

1. Inclua a candidatura pelo fluxo nativo do Recrutamento e associe-a à vaga. Ao criar candidato, o addon copia os templates ativos que correspondem ao perfil (globais `all` e perfil específico) para o checklist.
2. Na aba **Processo Voigt** do candidato, crie avaliação em **Avaliações** e escolha o tipo: RH, técnica, diretoria, QAE 01, QAE 02, organizacional ou experiência. Informe o avaliador responsável, data e revisão aplicada.
3. Para QAE 01/02, registre a nota total manualmente após a aplicação humana da rubrica; o addon não avalia respostas. Confirme máximo e corte, por padrão 100 e 60, e clique **Calcular resultado**. Nota igual ou acima do corte resulta em Apto; abaixo, Inapto. Para QAE condicional, usuário Voigt Manager registra motivo e precisa ser diferente do avaliador.
4. Para RH/técnica e demais avaliações não-QAE, o avaliador atribuído ou Voigt Manager registra o resultado usando **Marcar apto**/**Marcar inapto**. Avaliação técnica cria critérios conforme o perfil da vaga; preencha evidência/resultado de cada critério e parecer. A decisão de cada critério não substitui a ação final da avaliação.
5. Só avance para estágio com gate RH/técnica após gravar avaliação correspondente com resultado Apto ou Liberado condicional. As etapas de entrevista e aprovações internas devem refletir a sequência definida pela PO 017, mas atividades e reuniões devem ser criadas pelo usuário/fluxo nativo: este addon não gera agenda automática.

### Etapa 4 - checklist RQ 052 e aptidão ocupacional

1. No checklist da candidatura, marque o item como **Solicitado** e, após recebimento, como **Recebido**. Use **Verificar** para gravar responsável e horário. Itens opcionais não impedem conclusão; itens obrigatórios precisam estar verificados.
2. Para dispensar item, Voigt Manager informa motivo e usa **Dispensar**. Dispensa de item obrigatório exige justificativa; não exclua itens já verificados ou dispensados.
3. Quando for o momento definido pela política, usuário Voigt Manager clica **Solicitar avaliação**. O addon cria registro pendente sem anexar diagnóstico ou resultado clínico.
4. O usuário de Saúde Ocupacional abre **Recrutamento > Processo Voigt > Avaliações de aptidão**, confere identificação mínima e registra **Registrar apto** ou **Registrar inapto**. Não escrever diagnóstico, prontuário ou detalhe clínico no chatter, nome do registro ou campos.
5. Para mover para estágio de admissão/documentação ou proposta, o último resultado ocupacional deve ser Apto. Inapto ou pendente bloqueia a transição. A seleção de exames e a interpretação pertencem ao profissional competente, fora deste addon.

### Etapa 5 - proposta e contratação

Antes de usar estágio configurado como proposta, confirme: vaga associada à RQ 077 aprovada; documentos obrigatórios verificados ou dispensados; aptidão Apto. O addon não cria proposta, contrato de experiência nem prazo contratual 45+45 automaticamente; use os módulos/fluxos de RH e parâmetros aprovados pela empresa.

Ao mover candidatura para um estágio nativo com **Hired Stage/Etapa contratada** marcado, o addon cria um único registro de integração RQ 006. O empregado continua sendo o registro nativo `hr.employee` ligado à candidatura; o addon não duplica o cadastro de empregado. Se a contratação nativa não criar/vincular empregado, ajuste-a antes de depender do campo relacionado `employee_id`.

### Etapa 6 - integração, treinamento e PRÁTICO (RQ 006)

1. Um Voigt Manager abre **Recrutamento > Processo Voigt > Integração RQ 006** e localiza a integração gerada. A permissão do modelo de integração é restrita ao grupo Voigt Manager, mesmo que o menu de recrutamento apareça para outros usuários.
2. Confirme data de admissão, líder/Anjo da Guarda, treinamentos de RH, Qualidade, Segurança e operação, e entrega de fichas técnicas/documentos. Datas padrão: avaliação de habilidades em 15 dias e acompanhamento em 30 dias; são editáveis.
3. Para Rebarbação/Moldagem, confirme área compatível, treinamento da tarefa e entrega/conferência de EPIs. Para Mecânico, registre treinamento dos equipamentos e rotinas aplicáveis. O perfil vem da vaga e define quais campos específicos aparecem e são exigidos.
4. O módulo cria nove itens de habilidade e dez de atitude. O avaliador preenche cada nota com 0, 1, 3 ou 5 e anota evidências. A pontuação final não é calculada automaticamente.
5. **Aprovar liberação PRÁTICO** só fica disponível para Voigt Manager e a ação verifica todos os treinamentos gerais, responsável operacional, documentos técnicos e exigências específicas de perfil. Se faltar algo, a ação retorna erro e não libera.
6. Após a avaliação completa, Voigt Manager registra **Efetivar**, **Acompanhar / adequar** ou **Encerrar**. Todas as 19 linhas precisam estar avaliadas; a decisão grava usuário e horário. Atualize as datas de acompanhamento conforme decisão do RH e divergência entre PO 017 (uma semana) e RQ 006 (15–30 dias).

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
