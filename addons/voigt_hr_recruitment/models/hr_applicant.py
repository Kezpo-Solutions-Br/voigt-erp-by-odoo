from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    voigt_assessment_ids = fields.One2many('voigt.applicant.assessment', 'applicant_id', string='Avaliações Voigt')
    voigt_document_ids = fields.One2many('voigt.applicant.document', 'applicant_id', string='Checklist admissional')
    voigt_onboarding_ids = fields.One2many('voigt.onboarding', 'applicant_id', string='Integração')
    voigt_checklist_complete = fields.Boolean(compute='_compute_voigt_checklist_complete')
    voigt_occupational_assessment_ids = fields.One2many(
        'voigt.occupational.assessment', 'applicant_id', string='Avaliações ocupacionais',
    )
    voigt_occupational_fitness = fields.Selection([
        ('not_requested', 'Não solicitado'), ('pending', 'Pendente'),
        ('fit', 'Apto'), ('unfit', 'Inapto'),
    ], compute='_compute_voigt_occupational_fitness', groups='voigt_hr_recruitment.group_voigt_recruitment_manager')

    @api.depends('voigt_occupational_assessment_ids.status')
    def _compute_voigt_occupational_fitness(self):
        assessments = self.env['voigt.occupational.assessment'].sudo().search_fetch(
            [('applicant_id', 'in', self.ids)], ['applicant_id', 'status'], order='id desc',
        )
        status_by_applicant = {}
        for assessment in assessments:
            status_by_applicant.setdefault(assessment.applicant_id.id, assessment.status)
        for applicant in self:
            applicant.voigt_occupational_fitness = status_by_applicant.get(applicant.id, 'not_requested')

    @api.depends('voigt_document_ids.state', 'voigt_document_ids.required')
    def _compute_voigt_checklist_complete(self):
        documents = self.env['voigt.applicant.document'].sudo().search_fetch(
            [('applicant_id', 'in', self.ids), ('required', '=', True)], ['applicant_id', 'state']
        )
        documents_by_applicant = {}
        for document in documents:
            documents_by_applicant.setdefault(document.applicant_id.id, []).append(document.state)
        for applicant in self:
            states = documents_by_applicant.get(applicant.id, [])
            applicant.voigt_checklist_complete = bool(states) and all(
                state in ('verified', 'waived') for state in states
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any('voigt_occupational_fitness' in vals for vals in vals_list):
            raise ValidationError(self.env._('Occupational fitness is computed from its restricted assessment record.'))
        applicants = super().create(vals_list)
        for applicant in applicants:
            templates = self.env['voigt.applicant.document.template'].sudo().search([
                ('active', '=', True), ('profile', 'in', ['all', applicant.job_id.voigt_profile]),
            ])
            self.env['voigt.applicant.document'].sudo().create([
                {
                    'applicant_id': applicant.id, 'name': template.name,
                    'sequence': template.sequence, 'required': template.required,
                }
                for template in templates
            ])
        applicants._create_voigt_onboarding_for_hired()
        return applicants

    def write(self, vals):
        if 'voigt_occupational_fitness' in vals:
            raise UserError(self.env._('Occupational fitness is computed from its restricted assessment record.'))
        if 'stage_id' in vals:
            target_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            for applicant in self:
                gate = target_stage.voigt_gate
                if gate == 'screening' and not applicant.voigt_assessment_ids.filtered(lambda item: item.assessment_type == 'hr' and item.result in ('approved', 'conditional')):
                    raise UserError(self.env._('Complete and pass the RH screening assessment before this stage.'))
                if gate == 'technical' and not applicant.voigt_assessment_ids.filtered(lambda item: item.assessment_type == 'technical' and item.result in ('approved', 'conditional')):
                    raise UserError(self.env._('Complete and pass the technical assessment before this stage.'))
                if gate == 'admission' and not applicant.voigt_checklist_complete:
                    raise UserError(self.env._('Verify or formally waive all required admission checklist items first.'))
                occupational_fitness = applicant.sudo().voigt_occupational_fitness
                if gate in ('admission', 'offer') and occupational_fitness != 'fit':
                    raise UserError(self.env._('The authorized occupational fitness result must be Apto before this stage.'))
                if gate == 'offer':
                    if not applicant.voigt_checklist_complete:
                        raise UserError(self.env._('Complete the required admission checklist before making an offer.'))
                    if not applicant.job_id.voigt_request_id or applicant.job_id.voigt_request_id.state != 'approved':
                        raise UserError(self.env._('The linked RQ 077 request must be approved before an offer.'))
        result = super().write(vals)
        if 'stage_id' in vals:
            self._create_voigt_onboarding_for_hired()
        return result

    def _create_voigt_onboarding_for_hired(self):
        hired_applicants = self.filtered(lambda applicant: applicant.stage_id.hired_stage)
        if not hired_applicants:
            return
        existing_applicant_ids = self.env['voigt.onboarding'].sudo().search_fetch(
            [('applicant_id', 'in', hired_applicants.ids)], ['applicant_id']
        ).mapped('applicant_id').ids
        applicants_to_initialize = hired_applicants.filtered(lambda applicant: applicant.id not in existing_applicant_ids)
        if applicants_to_initialize:
            self.env['voigt.onboarding'].sudo().create([
                {'applicant_id': applicant.id, 'admission_date': fields.Date.context_today(self)}
                for applicant in applicants_to_initialize
            ])

    def action_request_occupational_fitness(self):
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager'):
            raise UserError(self.env._('Only Voigt recruitment managers can request occupational assessment.'))
        for applicant in self:
            self.env['voigt.occupational.assessment'].create({
                'applicant_id': applicant.id,
            })
