from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VoigtOnboarding(models.Model):
    _name = 'voigt.onboarding'
    _description = 'Voigt Onboarding (RQ 006)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='restrict', index=True)
    employee_id = fields.Many2one(related='applicant_id.employee_id', readonly=True, store=True)
    admission_date = fields.Date(required=True, tracking=True)
    profile = fields.Selection(related='applicant_id.job_id.voigt_profile', store=True, readonly=True)
    hr_training_done = fields.Boolean(tracking=True)
    quality_training_done = fields.Boolean(tracking=True)
    safety_training_done = fields.Boolean(tracking=True)
    operational_training_done = fields.Boolean(tracking=True)
    operational_trainer_id = fields.Many2one('hr.employee', tracking=True, help='Líder ou Anjo da Guarda responsável pelo treinamento no posto.')
    technical_documents_done = fields.Boolean(tracking=True, help='Fichas técnicas e especificações repassadas ao colaborador.')
    production_area = fields.Selection([
        ('rebarbacao', 'Acabamento / Rebarbação'), ('moldagem', 'Moldagem'),
    ], tracking=True)
    production_task_trained = fields.Boolean(tracking=True, help='Tarefa específica do setor repassada sob supervisão.')
    ppe_issue_verified = fields.Boolean(tracking=True, help='EPIs do posto e treinamento de uso conferidos.')
    mechanic_equipment_training = fields.Boolean(tracking=True, help='Equipamentos e rotinas de manutenção aplicáveis repassados.')
    practical_done = fields.Boolean(tracking=True, help='Item PRÁTICO do RQ 006 concluído.')
    practical_approved_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    practical_approved_at = fields.Datetime(readonly=True, tracking=True)
    evaluation_date = fields.Date(help='Avaliação de habilidades e atitudes, prevista entre 15 e 30 dias.')
    probation_followup_date = fields.Date(help='Avaliação intermediária de 30 ou 45 dias, quando necessária.')
    final_evaluation = fields.Selection([
        ('pending', 'Pendente'), ('confirmed', 'Efetivado'),
        ('extended', 'Adequação / acompanhamento'), ('ended', 'Encerrado'),
    ], default='pending', required=True, tracking=True)
    evaluation_notes = fields.Text(tracking=True)
    skill_ids = fields.One2many('voigt.onboarding.skill', 'onboarding_id', string='Avaliação RQ 006')
    final_evaluation_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    final_evaluation_at = fields.Datetime(readonly=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            protected_fields = {
                'practical_done', 'practical_approved_by_id', 'practical_approved_at',
                'final_evaluation', 'final_evaluation_by_id', 'final_evaluation_at',
            }
            if protected_fields.intersection(vals):
                raise ValidationError(self.env._('New onboarding records must start without practical or final approvals.'))
            admission_date = fields.Date.to_date(vals.get('admission_date'))
            applicant = self.env['hr.applicant'].browse(vals.get('applicant_id'))
            if applicant.job_id.voigt_profile == 'production_rebarbacao':
                vals.setdefault('production_area', 'rebarbacao')
            elif applicant.job_id.voigt_profile == 'production_moldagem':
                vals.setdefault('production_area', 'moldagem')
            if admission_date and not vals.get('evaluation_date'):
                vals['evaluation_date'] = admission_date + timedelta(days=15)
            if admission_date and not vals.get('probation_followup_date'):
                vals['probation_followup_date'] = admission_date + timedelta(days=30)
        onboardings = super().create(vals_list)
        templates = self.env['voigt.onboarding.skill.template'].search([('active', '=', True)])
        for onboarding in onboardings:
            onboarding.skill_ids = [Command.create({
                'sequence': template.sequence, 'kind': template.kind, 'name': template.name,
            }) for template in templates]
        return onboardings

    def write(self, vals):
        protected_fields = {
            'practical_done', 'practical_approved_by_id', 'practical_approved_at',
            'final_evaluation', 'final_evaluation_by_id', 'final_evaluation_at',
        }
        if protected_fields.intersection(vals):
            raise UserError(self.env._('Use the practical release action to record PRÁTICO approval.'))
        return super().write(vals)

    _applicant_unique = models.UniqueIndex('(applicant_id)')

    @api.constrains('profile', 'production_area')
    def _check_production_area(self):
        area_by_profile = {
            'production_rebarbacao': 'rebarbacao', 'production_moldagem': 'moldagem',
        }
        for onboarding in self:
            expected_area = area_by_profile.get(onboarding.profile)
            if expected_area and onboarding.production_area and onboarding.production_area != expected_area:
                raise ValidationError(self.env._('The production area must match the position profile.'))

    def action_approve_practical(self):
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager'):
            raise UserError(self.env._('Only Voigt recruitment managers can approve practical release.'))
        for onboarding in self:
            if not onboarding.hr_training_done or not onboarding.quality_training_done or not onboarding.safety_training_done:
                raise UserError(self.env._('Complete RH, Quality and Safety training before approving practical release.'))
            if not onboarding.operational_training_done or not onboarding.technical_documents_done:
                raise UserError(self.env._('Complete operational training and document handover before practical release.'))
            if not onboarding.operational_trainer_id:
                raise UserError(self.env._('Assign a leader or Guardian Angel before practical release.'))
            if onboarding.profile in ('production_rebarbacao', 'production_moldagem') and (
                not onboarding.production_area or not onboarding.production_task_trained or not onboarding.ppe_issue_verified
            ):
                raise UserError(self.env._('Complete position-specific task training and PPE verification before practical release.'))
            if onboarding.profile == 'mechanic' and not onboarding.mechanic_equipment_training:
                raise UserError(self.env._('Complete maintenance equipment training before practical release.'))
            super(VoigtOnboarding, onboarding).write({
                'practical_done': True, 'practical_approved_by_id': self.env.user.id,
                'practical_approved_at': fields.Datetime.now(),
            })

    def action_confirm_effective(self):
        self._action_finalize_evaluation('confirmed')

    def action_extend_probation(self):
        self._action_finalize_evaluation('extended')

    def action_end_probation(self):
        self._action_finalize_evaluation('ended')

    def _action_finalize_evaluation(self, result):
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager'):
            raise UserError(self.env._('Only Voigt recruitment managers can record the final evaluation.'))
        for onboarding in self:
            if not onboarding.skill_ids or any(skill.rating is False for skill in onboarding.skill_ids):
                raise UserError(self.env._('Rate every RQ 006 skill and attitude before the final decision.'))
            super(VoigtOnboarding, onboarding).write({
                'final_evaluation': result, 'final_evaluation_by_id': self.env.user.id,
                'final_evaluation_at': fields.Datetime.now(),
            })
