from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class VoigtApplicantDocument(models.Model):
    _name = 'voigt.applicant.document'
    _description = 'Voigt Admission Checklist Item (RQ 052)'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    required = fields.Boolean(default=True)
    state = fields.Selection([
        ('not_requested', 'Não solicitado'), ('requested', 'Solicitado'),
        ('received', 'Recebido'), ('verified', 'Verificado'), ('waived', 'Dispensado'),
    ], default='not_requested', required=True, tracking=True)
    verified_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    verified_at = fields.Datetime(readonly=True, tracking=True)
    waiver_reason = fields.Text(tracking=True)
    attachment_id = fields.Many2one('ir.attachment', string='Evidência')

    @api.model_create_multi
    def create(self, vals_list):
        if any(
            vals.get('state', 'not_requested') not in ('not_requested', 'requested', 'received')
            or vals.get('verified_by_id') or vals.get('verified_at')
            for vals in vals_list
        ):
            raise ValidationError(self.env._('Checklist items must start unverified. Use the checklist actions to record verification.'))
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {'verified_by_id', 'verified_at'}
        if protected_fields.intersection(vals) or vals.get('state') in ('verified', 'waived'):
            raise UserError(self.env._('Use the checklist actions to verify or waive an item.'))
        return super().write(vals)

    @api.constrains('state', 'required', 'waiver_reason')
    def _check_waiver_reason(self):
        for item in self:
            if item.state == 'waived' and item.required and not item.waiver_reason:
                raise UserError(self.env._('A reason is required to waive a required checklist item.'))

    def action_verify(self):
        for item in self:
            if item.state != 'received':
                raise UserError(self.env._('Only received items can be verified.'))
            super(VoigtApplicantDocument, item).write({
                'state': 'verified', 'verified_by_id': self.env.user.id, 'verified_at': fields.Datetime.now(),
            })

    def action_waive(self):
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager'):
            raise UserError(self.env._('Only Voigt recruitment managers can waive checklist items.'))
        for item in self:
            if not item.waiver_reason:
                raise UserError(self.env._('A reason is required to waive a checklist item.'))
            if item.state in ('verified', 'waived'):
                raise UserError(self.env._('Verified or waived checklist items cannot be waived again.'))
            super(VoigtApplicantDocument, item).write({
                'state': 'waived', 'verified_by_id': self.env.user.id, 'verified_at': fields.Datetime.now(),
            })

    def unlink(self):
        if any(item.state in ('verified', 'waived') for item in self):
            raise UserError(self.env._('Verified or waived checklist items cannot be deleted.'))
        return super().unlink()
