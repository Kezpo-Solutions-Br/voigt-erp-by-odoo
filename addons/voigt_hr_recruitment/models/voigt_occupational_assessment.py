from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class VoigtOccupationalAssessment(models.Model):
    _name = 'voigt.occupational.assessment'
    _description = 'Voigt Occupational Fitness Assessment'
    _inherit = ['mail.thread']
    _order = 'id desc'

    applicant_id = fields.Many2one(
        'hr.applicant', required=True, ondelete='restrict', index=True,
        groups='voigt_hr_recruitment.group_voigt_recruitment_manager',
    )
    candidate_name = fields.Char(
        related='applicant_id.partner_name',
        groups='voigt_hr_recruitment.group_voigt_occupational_health,base.group_system',
    )
    job_title = fields.Char(
        related='applicant_id.job_id.name',
        groups='voigt_hr_recruitment.group_voigt_occupational_health,base.group_system',
    )
    company_id = fields.Many2one(related='applicant_id.company_id', store=True, index=True)
    requested_by_id = fields.Many2one('res.users', required=True, readonly=True, default=lambda self: self.env.user)
    requested_at = fields.Datetime(required=True, readonly=True, default=fields.Datetime.now)
    status = fields.Selection([
        ('pending', 'Pendente'), ('fit', 'Apto'), ('unfit', 'Inapto'),
    ], default='pending', required=True, tracking=True)
    result_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    result_at = fields.Datetime(readonly=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        protected_fields = {'status', 'result_by_id', 'result_at', 'requested_by_id', 'requested_at'}
        if any(protected_fields.intersection(vals) for vals in vals_list):
            raise ValidationError(self.env._('New occupational assessments must start pending.'))
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {'status', 'result_by_id', 'result_at', 'requested_by_id', 'requested_at'}
        if protected_fields.intersection(vals):
            raise UserError(self.env._('Use the occupational assessment actions to record a result.'))
        return super().write(vals)

    def action_mark_fit(self):
        self._action_record_result('fit')

    def action_mark_unfit(self):
        self._action_record_result('unfit')

    def _action_record_result(self, status):
        is_occupational_health = self.env.user.has_group('voigt_hr_recruitment.group_voigt_occupational_health')
        is_system_admin = self.env.user.has_group('base.group_system')
        if not (is_occupational_health or is_system_admin):
            raise UserError(self.env._('Only the Voigt occupational health group can record fitness results.'))
        for assessment in self:
            if assessment.status != 'pending':
                raise UserError(self.env._('Only pending occupational assessments can receive a result.'))
            super(VoigtOccupationalAssessment, assessment).write({
                'status': status, 'result_by_id': self.env.user.id, 'result_at': fields.Datetime.now(),
            })
        applicants = self.sudo().mapped('applicant_id')
        applicants.invalidate_recordset(['voigt_occupational_fitness'])

    def unlink(self):
        raise UserError(self.env._('Occupational assessment records cannot be deleted.'))
