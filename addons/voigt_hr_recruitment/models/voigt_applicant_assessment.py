from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VoigtApplicantAssessment(models.Model):
    _name = 'voigt.applicant.assessment'
    _description = 'Voigt Applicant Assessment'
    _inherit = ['mail.thread']
    _order = 'assessment_date desc, id desc'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade', index=True)
    assessment_type = fields.Selection([
        ('hr', 'Entrevista RH'), ('technical', 'Entrevista técnica'),
        ('director', 'Entrevista diretoria'), ('qae_01', 'QAE 01 / RQ 079'),
        ('qae_02', 'QAE 02 / RQ 081'), ('psychological', 'Avaliação organizacional'),
        ('probation', 'Avaliação de experiência'),
    ], required=True, tracking=True)
    assessor_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, tracking=True)
    assessment_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    revision = fields.Char(help='Revisão do formulário ou rubrica aplicada.')
    score = fields.Float(tracking=True, help='Pontuação total, quando aplicável.')
    maximum_score = fields.Float(default=100.0)
    cutoff_score = fields.Float(default=60.0, help='Corte da revisão aplicada; QAE 01 Rev. B usa 60/100.')
    result = fields.Selection([
        ('pending', 'Pendente'), ('approved', 'Apto'), ('rejected', 'Inapto'),
        ('conditional', 'Liberado condicional'),
    ], default='pending', required=True, tracking=True)
    comments = fields.Text(
        tracking=True, groups='voigt_hr_recruitment.group_voigt_recruitment_manager',
        help='Parecer de recrutamento. Não registrar informações clínicas ou diagnósticos.',
    )
    psychological_summary = fields.Text(
        groups='voigt_hr_recruitment.group_voigt_psychologist',
        help='Registrar somente parecer ocupacional resumido; não registrar diagnóstico ou notas clínicas.',
    )
    conditional_reason = fields.Text(tracking=True, groups='voigt_hr_recruitment.group_voigt_recruitment_manager')
    conditional_approver_id = fields.Many2one('res.users', readonly=True, tracking=True)
    conditional_approved_at = fields.Datetime(readonly=True, tracking=True)
    criterion_ids = fields.One2many('voigt.applicant.assessment.criterion', 'assessment_id', string='Critérios da vaga')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('result', 'pending') != 'pending':
                raise ValidationError(self.env._('Assessments must start as pending. Use an assessment action to record a decision.'))
            assessment_type = vals.get('assessment_type')
            if assessment_type == 'qae_01':
                vals.setdefault('revision', 'RQ 079 Rev. B')
            elif assessment_type == 'qae_02':
                vals.setdefault('revision', 'RQ 081 Rev. B')
        assessments = super().create(vals_list)
        for assessment in assessments.filtered(lambda item: item.assessment_type == 'technical'):
            templates = self.env['voigt.assessment.criterion.template'].search([
                ('profile', '=', assessment.applicant_id.job_id.voigt_profile),
                ('assessment_type', '=', 'technical'), ('active', '=', True),
            ])
            if templates:
                assessment.criterion_ids = [Command.create({'name': template.name}) for template in templates]
        return assessments

    def write(self, vals):
        protected_fields = {'result', 'conditional_approver_id', 'conditional_approved_at'}
        if protected_fields.intersection(vals):
            raise UserError(self.env._('Use an assessment action to record a decision.'))
        if {'score', 'maximum_score', 'cutoff_score'}.intersection(vals):
            return super().write(dict(
                vals, result='pending', conditional_approver_id=False, conditional_approved_at=False,
            ))
        return super().write(vals)



    @api.constrains('score', 'maximum_score', 'cutoff_score', 'assessment_type')
    def _check_score(self):
        for assessment in self:
            if assessment.score < 0 or assessment.maximum_score <= 0 or assessment.score > assessment.maximum_score:
                raise ValidationError(self.env._('Assessment score must be between zero and the maximum score.'))
            if not 0 <= assessment.cutoff_score <= assessment.maximum_score:
                raise ValidationError(self.env._('The cutoff must be between zero and the maximum score.'))

    def action_evaluate(self):
        for assessment in self:
            assessment._check_assessor()
            if assessment.assessment_type not in ('qae_01', 'qae_02'):
                raise UserError(self.env._('Scored evaluation is only available for QAE assessments.'))
            result = 'approved' if assessment.score >= assessment.cutoff_score else 'rejected'
            super(VoigtApplicantAssessment, assessment).write({'result': result})

    def action_mark_approved(self):
        for assessment in self:
            assessment._check_assessor()
            if assessment.assessment_type in ('qae_01', 'qae_02'):
                raise UserError(self.env._('Use the score calculation for QAE assessments.'))
            super(VoigtApplicantAssessment, assessment).write({'result': 'approved'})

    def action_mark_rejected(self):
        for assessment in self:
            assessment._check_assessor()
            if assessment.assessment_type in ('qae_01', 'qae_02'):
                raise UserError(self.env._('Use the score calculation for QAE assessments.'))
            super(VoigtApplicantAssessment, assessment).write({'result': 'rejected'})

    def action_approve_conditionally(self):
        is_system_admin = self.env.user.has_group('base.group_system')
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager') and not is_system_admin:
            raise UserError(self.env._('Only Voigt recruitment managers can grant conditional approval.'))
        for assessment in self:
            if not assessment.conditional_reason:
                raise UserError(self.env._('A reason is required for conditional approval.'))
            if assessment.assessor_id == self.env.user and not is_system_admin:
                raise UserError(self.env._('The assessor cannot approve their own conditional assessment.'))
            super(VoigtApplicantAssessment, assessment).write({
                'result': 'conditional', 'conditional_approver_id': self.env.user.id,
                'conditional_approved_at': fields.Datetime.now(),
            })

    def _check_assessor(self):
        self.ensure_one()
        if self.assessor_id != self.env.user and not self.env.user.has_group(
            'voigt_hr_recruitment.group_voigt_recruitment_manager'
        ):
            raise UserError(self.env._('Only the assigned assessor or a Voigt recruitment manager can record this decision.'))
