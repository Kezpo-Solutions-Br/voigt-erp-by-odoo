from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.base.tests.common import BaseCommon


class TestVoigtRecruitment(BaseCommon):
    _test_user_groups = (
        'hr_recruitment.group_hr_recruitment_manager',
        'voigt_hr_recruitment.group_voigt_recruitment_manager',
        'voigt_hr_recruitment.group_voigt_occupational_health',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.department = cls.env['hr.department'].create({
            'name': 'Voigt Test Department', 'company_id': cls.company.id,
        })
        cls.job = cls.env['hr.job'].create({
            'name': 'Auxiliar de Produção - Teste', 'company_id': cls.company.id,
            'department_id': cls.department.id, 'voigt_profile': 'production_rebarbacao',
        })
        cls.screening_stage = cls.env['hr.recruitment.stage'].create({
            'name': 'Triagem RH - Teste', 'sequence': 50, 'voigt_gate': 'screening',
        })

    def test_request_requires_replacement_target_and_positive_quantity(self):
        with self.assertRaises(ValidationError):
            self.env['voigt.recruitment.request'].create({
                'department_id': self.department.id, 'job_title': 'Operador',
                'employment_type': 'permanent', 'reason': 'replacement',
                'justification': 'Reposição aprovada', 'work_schedule': 'Turno diurno',
                'salary_reference': 'Faixa vigente', 'replacement_for': False,
            })

    def test_request_submission_starts_approval_flow(self):
        request = self.env['voigt.recruitment.request'].create({
            'department_id': self.department.id, 'job_title': 'Operador',
            'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Aumento aprovado no orçamento', 'work_schedule': 'Turno diurno',
            'salary_reference': 'Faixa vigente',
        })
        request.action_submit()
        self.assertEqual(request.state, 'to_approve')
        with self.assertRaises(UserError):
            request.write({'state': 'approved'})

    def test_request_form_can_create_explicit_draft_with_empty_approval_fields(self):
        request = self.env['voigt.recruitment.request'].create({
            'department_id': self.department.id, 'job_title': 'Auxiliar de Produção',
            'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Reposição planejada da capacidade do setor.',
            'work_schedule': 'Turno conforme escala do setor', 'salary_reference': 'Faixa aprovada',
            'quantity': 1, 'requester_id': self.env.user.id, 'state': 'draft',
            'department_approver_id': False, 'department_approved_at': False,
            'director_approver_id': False, 'director_approved_at': False,
        })
        self.assertEqual(request.state, 'draft')
        self.assertFalse(request.department_approver_id)
        self.assertFalse(request.director_approver_id)

    def test_system_administrator_can_complete_test_approvals_for_own_request(self):
        administrator = self.env.ref('base.user_admin')
        self.assertTrue(administrator.has_group('base.group_system'))
        request = self.env['voigt.recruitment.request'].with_user(administrator).create({
            'department_id': self.department.id, 'job_title': 'Auxiliar de Produção',
            'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Aumento de capacidade previsto para o setor.',
            'work_schedule': 'Turno conforme escala do setor', 'salary_reference': 'Faixa aprovada',
            'quantity': 1, 'requester_id': administrator.id, 'state': 'draft',
            'department_approver_id': False, 'department_approved_at': False,
            'director_approver_id': False, 'director_approved_at': False,
        })
        request.with_user(administrator).action_submit()
        request.with_user(administrator).action_approve_department()
        request.with_user(administrator).action_approve_director()
        self.assertEqual(request.state, 'approved')
        self.assertEqual(request.department_approver_id, administrator)
        self.assertEqual(request.director_approver_id, administrator)

    def test_regular_requester_still_cannot_approve_own_request(self):
        requester = self.env['res.users'].sudo().create({
            'name': 'Requisitante comum de teste', 'login': 'voigt-requester-test',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('hr_recruitment.group_hr_recruitment_user').id,
            ])],
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
        })
        request = self.env['voigt.recruitment.request'].sudo().create({
            'company_id': self.company.id, 'department_id': self.department.id,
            'job_title': 'Operador - teste', 'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Solicitação fictícia de teste.', 'work_schedule': 'Turno de teste',
            'salary_reference': 'Faixa de teste', 'requester_id': requester.id,
        })
        request.with_user(requester).action_submit()
        with self.assertRaises(UserError):
            request.with_user(requester).action_approve_department()

    def test_system_administrator_can_complete_occupational_result_for_testing(self):
        administrator = self.env.ref('base.user_admin')
        applicant = self.env['hr.applicant'].sudo().create({
            'partner_name': 'Candidato fictício para teste', 'job_id': self.job.id,
        })
        assessment = self.env['voigt.occupational.assessment'].sudo().create({
            'applicant_id': applicant.id,
        })
        assessment.with_user(administrator).action_mark_fit()
        self.assertEqual(assessment.status, 'fit')
        self.assertEqual(assessment.result_by_id, administrator)

    def test_system_administrator_can_grant_conditional_approval_to_own_assessment(self):
        administrator = self.env.ref('base.user_admin')
        applicant = self.env['hr.applicant'].sudo().create({
            'partner_name': 'Candidato fictício para teste', 'job_id': self.job.id,
        })
        assessment = self.env['voigt.applicant.assessment'].sudo().create({
            'applicant_id': applicant.id, 'assessment_type': 'qae_01',
            'assessor_id': administrator.id,
            'conditional_reason': 'Exceção de demonstração do fluxo administrativo.',
        })
        assessment.with_user(administrator).action_approve_conditionally()
        self.assertEqual(assessment.result, 'conditional')
        self.assertEqual(assessment.conditional_approver_id, administrator)

    def test_administrator_can_complete_tutorial_flow_end_to_end(self):
        administrator = self.env.ref('base.user_admin')
        request = self.env['voigt.recruitment.request'].with_user(administrator).create({
            'company_id': self.company.id, 'department_id': self.department.id,
            'job_title': 'Auxiliar de Produção - Rebarbação', 'quantity': 1,
            'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Caso fictício para validar o tutorial do addon.',
            'work_schedule': 'Turno de teste', 'salary_reference': 'Faixa de demonstração',
            'requester_id': administrator.id, 'state': 'draft',
            'department_approver_id': False, 'department_approved_at': False,
            'director_approver_id': False, 'director_approved_at': False,
        })
        request.with_user(administrator).action_submit()
        request.with_user(administrator).action_approve_department()
        request.with_user(administrator).action_approve_director()

        job = self.env['hr.job'].with_user(administrator).create({
            'name': 'Auxiliar de Produção - Rebarbação (Treinamento)',
            'company_id': self.company.id, 'department_id': self.department.id,
            'voigt_profile': 'production_rebarbacao', 'voigt_request_id': request.id,
        })
        applicant = self.env['hr.applicant'].with_user(administrator).create({
            'partner_name': 'Candidato Fictício Voigt - Treinamento', 'job_id': job.id,
            'company_id': self.company.id,
        })

        hr_stage = self.env['hr.recruitment.stage'].with_user(administrator).create({
            'name': 'Entrevista RH - Tutorial', 'voigt_gate': 'screening',
        })
        technical_stage = self.env['hr.recruitment.stage'].with_user(administrator).create({
            'name': 'Entrevista técnica - Tutorial', 'voigt_gate': 'technical',
        })
        admission_stage = self.env['hr.recruitment.stage'].with_user(administrator).create({
            'name': 'Admissão - Tutorial', 'voigt_gate': 'admission',
        })
        offer_stage = self.env['hr.recruitment.stage'].with_user(administrator).create({
            'name': 'Proposta - Tutorial', 'voigt_gate': 'offer',
        })
        hired_stage = self.env['hr.recruitment.stage'].with_user(administrator).create({
            'name': 'Contratado - Tutorial', 'hired_stage': True,
        })

        hr_assessment = self.env['voigt.applicant.assessment'].with_user(administrator).create({
            'applicant_id': applicant.id, 'assessment_type': 'hr', 'assessor_id': administrator.id,
        })
        hr_assessment.with_user(administrator).action_mark_approved()
        applicant.with_user(administrator).write({'stage_id': hr_stage.id})
        technical_assessment = self.env['voigt.applicant.assessment'].with_user(administrator).create({
            'applicant_id': applicant.id, 'assessment_type': 'technical', 'assessor_id': administrator.id,
        })
        technical_assessment.with_user(administrator).action_mark_approved()
        applicant.with_user(administrator).write({'stage_id': technical_stage.id})

        required_documents = applicant.voigt_document_ids.filtered(lambda item: item.required)
        required_documents.with_user(administrator).write({'state': 'received'})
        required_documents.with_user(administrator).action_verify()
        applicant.with_user(administrator).action_request_occupational_fitness()
        occupational_assessment = applicant.voigt_occupational_assessment_ids
        occupational_assessment.with_user(administrator).action_mark_fit()
        applicant.with_user(administrator).write({'stage_id': admission_stage.id})
        applicant.with_user(administrator).write({'stage_id': offer_stage.id})
        applicant.with_user(administrator).write({'stage_id': hired_stage.id})

        onboarding = self.env['voigt.onboarding'].with_user(administrator).search(
            [('applicant_id', '=', applicant.id)], limit=1,
        )
        self.assertTrue(onboarding)
        trainer = self.env['hr.employee'].sudo().create({
            'name': 'Líder Fictício de Treinamento', 'company_id': self.company.id,
        })
        onboarding.with_user(administrator).write({
            'hr_training_done': True, 'quality_training_done': True, 'safety_training_done': True,
            'operational_training_done': True, 'operational_trainer_id': trainer.id,
            'technical_documents_done': True, 'production_task_trained': True,
            'ppe_issue_verified': True,
        })
        onboarding.with_user(administrator).action_approve_practical()
        onboarding.skill_ids.with_user(administrator).write({'rating': '3'})
        onboarding.with_user(administrator).action_confirm_effective()

        self.assertTrue(onboarding.practical_done)
        self.assertEqual(onboarding.final_evaluation, 'confirmed')
        self.assertEqual(applicant.stage_id, hired_stage)

    def test_request_requires_two_distinct_approvers_and_reopens_when_changed(self):
        group_ids = [
            self.env.ref('base.group_user').id,
            self.env.ref('voigt_hr_recruitment.group_voigt_recruitment_manager').id,
        ]
        department_user = self.env['res.users'].sudo().create({
            'name': 'Aprovador setor teste', 'login': 'voigt-dept-approver',
            'group_ids': [(6, 0, group_ids)], 'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
        })
        director_user = self.env['res.users'].sudo().create({
            'name': 'Aprovador diretoria teste', 'login': 'voigt-director-approver',
            'group_ids': [(6, 0, group_ids)], 'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
        })
        department_employee = self.env['hr.employee'].sudo().create({
            'name': 'Responsável do setor', 'user_id': department_user.id,
            'company_id': self.company.id,
        })
        self.department.sudo().write({'manager_id': department_employee.id})
        request = self.env['voigt.recruitment.request'].create({
            'department_id': self.department.id, 'job_title': 'Técnico',
            'employment_type': 'permanent', 'reason': 'headcount',
            'justification': 'Vaga aprovada no planejamento', 'work_schedule': 'Horário do setor',
            'salary_reference': 'Faixa vigente',
        })
        request.action_submit()
        self.env.invalidate_all()
        request.with_user(department_user).action_approve_department()
        self.env.invalidate_all()
        request.with_user(director_user).action_approve_director()
        self.assertEqual(request.state, 'approved')
        request.write({'salary_reference': 'Nova faixa aprovada'})
        self.assertEqual(request.state, 'draft')
        self.assertFalse(request.department_approver_id)

    def test_stage_gate_blocks_unassessed_candidate(self):
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Candidato de teste', 'job_id': self.job.id,
        })
        with self.assertRaises(UserError):
            applicant.write({'stage_id': self.screening_stage.id})

    def test_qae_cutoff_calculates_result(self):
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Candidata QAE', 'job_id': self.job.id,
        })
        assessment = self.env['voigt.applicant.assessment'].create({
            'applicant_id': applicant.id, 'assessment_type': 'qae_01',
            'assessor_id': self.env.user.id, 'revision': 'RQ 079 Rev. B',
            'score': 59, 'maximum_score': 100, 'cutoff_score': 60,
        })
        assessment.action_evaluate()
        self.assertEqual(assessment.result, 'rejected')
        with self.assertRaises(UserError):
            assessment.write({'result': 'approved'})
        assessment.score = 60
        assessment.action_evaluate()
        self.assertEqual(assessment.result, 'approved')
        assessment.score = 59
        self.assertEqual(assessment.result, 'pending')

    def test_conditional_approval_requires_reason(self):
        applicant = self.env['hr.applicant'].create({'partner_name': 'Candidato QAE', 'job_id': self.job.id})
        assessor = self.env['res.users'].sudo().create({
            'name': 'Avaliador teste', 'login': 'voigt-assessor-test',
            'group_ids': [(6, 0, [self.env.ref('hr_recruitment.group_hr_recruitment_user').id])],
        })
        assessment = self.env['voigt.applicant.assessment'].create({
            'applicant_id': applicant.id, 'assessment_type': 'qae_01', 'assessor_id': assessor.id,
            'score': 55, 'maximum_score': 100, 'cutoff_score': 60,
        })
        with self.assertRaises(UserError):
            assessment.action_approve_conditionally()
        assessment.conditional_reason = 'Exceção aprovada pela área responsável.'
        assessment.action_approve_conditionally()
        self.assertEqual(assessment.result, 'conditional')
        self.assertEqual(assessment.conditional_approver_id, self.env.user)

    def test_admission_gate_requires_occupational_fitness(self):
        admission_stage = self.env['hr.recruitment.stage'].create({
            'name': 'Admissão - Teste', 'sequence': 60, 'voigt_gate': 'admission',
        })
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Candidato aptidão', 'job_id': self.job.id,
        })
        required_documents = applicant.voigt_document_ids.filtered(lambda document: document.required)
        required_documents.write({'state': 'received'})
        with self.assertRaises(UserError):
            required_documents[0].write({'state': 'verified'})
        required_documents.action_verify()
        with self.assertRaises(UserError):
            applicant.write({'stage_id': admission_stage.id})
        with self.assertRaises(UserError):
            applicant.write({'voigt_occupational_fitness': 'fit'})
        applicant.action_request_occupational_fitness()
        assessment = applicant.voigt_occupational_assessment_ids[-1]
        health_user = self.env['res.users'].sudo().create({
            'name': 'Saúde Ocupacional', 'login': 'voigt-occupational-health',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('voigt_hr_recruitment.group_voigt_occupational_health').id,
            ])],
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
        })
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.env['hr.applicant'].with_user(health_user).search_count([])
        health_assessment = assessment.with_user(health_user)
        self.assertEqual(health_assessment.candidate_name, applicant.partner_name)
        health_assessment.action_mark_fit()
        self.env.invalidate_all()
        self.assertEqual(assessment.status, 'fit')
        self.assertEqual(assessment.result_by_id, health_user)
        self.assertEqual(applicant.voigt_occupational_fitness, 'fit')
        applicant.write({'stage_id': admission_stage.id})
        self.assertEqual(applicant.stage_id, admission_stage)

    def test_onboarding_practical_release_requires_all_training(self):
        applicant = self.env['hr.applicant'].create({'partner_name': 'Candidato integração', 'job_id': self.job.id})
        onboarding = self.env['voigt.onboarding'].create({
            'applicant_id': applicant.id, 'admission_date': '2026-11-24',
        })
        with self.assertRaises(UserError):
            onboarding.action_approve_practical()
        with self.assertRaises(UserError):
            onboarding.action_confirm_effective()

    def test_mechanic_assessment_uses_position_specific_criteria(self):
        job = self.env['hr.job'].create({
            'name': 'Mecânico de Manutenção - Teste', 'company_id': self.company.id,
            'department_id': self.department.id, 'voigt_profile': 'mechanic',
        })
        applicant = self.env['hr.applicant'].create({'partner_name': 'Candidato mecânico', 'job_id': job.id})
        assessment = self.env['voigt.applicant.assessment'].create({
            'applicant_id': applicant.id, 'assessment_type': 'technical', 'assessor_id': self.env.user.id,
        })
        self.assertGreaterEqual(len(assessment.criterion_ids), 8)
        self.assertIn('Soldagem', assessment.criterion_ids[0].name)

    def test_production_practical_release_requires_position_training(self):
        applicant = self.env['hr.applicant'].create({'partner_name': 'Candidata produção', 'job_id': self.job.id})
        onboarding = self.env['voigt.onboarding'].create({
            'applicant_id': applicant.id, 'admission_date': '2026-11-24',
            'hr_training_done': True, 'quality_training_done': True, 'safety_training_done': True,
            'operational_training_done': True, 'technical_documents_done': True,
            'operational_trainer_id': self.env['hr.employee'].sudo().create({'name': 'Líder teste'}).id,
            'production_area': 'rebarbacao',
        })
        with self.assertRaises(UserError):
            onboarding.action_approve_practical()
        onboarding.write({'production_task_trained': True, 'ppe_issue_verified': True})
        onboarding.action_approve_practical()
        self.assertTrue(onboarding.practical_done)
        self.assertEqual(onboarding.evaluation_date.isoformat(), '2026-12-09')
        self.assertEqual(len(onboarding.skill_ids), 19)
        with self.assertRaises(UserError):
            onboarding.action_confirm_effective()
        onboarding.skill_ids.write({'rating': '3'})
        onboarding.action_confirm_effective()
        self.assertEqual(onboarding.final_evaluation, 'confirmed')
        self.assertEqual(onboarding.final_evaluation_by_id, self.env.user)
