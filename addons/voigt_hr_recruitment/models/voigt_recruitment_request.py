from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class VoigtRecruitmentRequest(models.Model):
    _name = 'voigt.recruitment.request'
    _description = 'Voigt Recruitment Request (RQ 077)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, tracking=True)
    department_id = fields.Many2one('hr.department', required=True, check_company=True, tracking=True)
    job_title = fields.Char(required=True, tracking=True)
    employment_type = fields.Selection([
        ('permanent', 'Efetivo'), ('temporary', 'Temporário'), ('intern', 'Estagiário'),
    ], required=True, tracking=True)
    reason = fields.Selection([
        ('headcount', 'Aumento do quadro'), ('replacement', 'Substituição'), ('other', 'Outros'),
    ], required=True, tracking=True)
    justification = fields.Text(required=True, tracking=True)
    replacement_for = fields.Char(tracking=True)
    work_schedule = fields.Text(required=True, tracking=True)
    salary_reference = fields.Char(required=True, tracking=True)
    quantity = fields.Integer(required=True, default=1, tracking=True)
    requester_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, tracking=True)
    department_approver_id = fields.Many2one('res.users', tracking=True, readonly=True)
    department_approved_at = fields.Datetime(readonly=True, tracking=True)
    director_approver_id = fields.Many2one('res.users', tracking=True, readonly=True)
    director_approved_at = fields.Datetime(readonly=True, tracking=True)
    approval_comment = fields.Text(tracking=True)
    state = fields.Selection([
        ('draft', 'Rascunho'), ('to_approve', 'Aguardando aprovação do setor'),
        ('to_director', 'Aguardando diretoria'), ('approved', 'Aprovada'),
        ('rejected', 'Rejeitada'), ('cancelled', 'Cancelada'), ('filled', 'Preenchida'),
    ], default='draft', required=True, tracking=True, index=True)
    job_ids = fields.One2many('hr.job', 'voigt_request_id', string='Vagas')

    @api.model_create_multi
    def create(self, vals_list):
        approval_fields = {
            'department_approver_id', 'department_approved_at',
            'director_approver_id', 'director_approved_at',
        }
        for vals in vals_list:
            if vals.get('state', 'draft') != 'draft' or any(vals.get(field) for field in approval_fields):
                raise ValidationError(self.env._('New requests must start in draft without approval records.'))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('voigt.recruitment.request') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        protected_values = {'state', 'department_approver_id', 'department_approved_at', 'director_approver_id', 'director_approved_at'}
        if protected_values.intersection(vals):
            raise UserError(self.env._('Use the request approval actions to change approval status.'))
        material_fields = {
            'company_id', 'department_id', 'job_title', 'employment_type', 'reason',
            'justification', 'replacement_for', 'work_schedule', 'salary_reference', 'quantity',
        }
        if material_fields.intersection(vals):
            approved_requests = self.filtered(lambda request: request.state == 'approved')
            if approved_requests:
                super(VoigtRecruitmentRequest, approved_requests).write({
                    'state': 'draft', 'department_approver_id': False, 'department_approved_at': False,
                    'director_approver_id': False, 'director_approved_at': False,
                })
        return super().write(vals)

    @api.constrains('quantity', 'reason', 'replacement_for')
    def _check_request_values(self):
        for request in self:
            if request.quantity < 1:
                raise ValidationError(self.env._('The requested quantity must be at least one.'))
            if request.reason == 'replacement' and not request.replacement_for:
                raise ValidationError(self.env._('Specify the position or employee being replaced.'))

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(self.env._('Only draft requests can be submitted.'))
            super(VoigtRecruitmentRequest, request).write({'state': 'to_approve'})

    def action_approve_department(self):
        is_system_admin = self.env.user.has_group('base.group_system')
        for request in self:
            if request.state != 'to_approve':
                raise UserError(self.env._('This request is not awaiting department approval.'))
            if request.requester_id == self.env.user and not is_system_admin:
                raise UserError(self.env._('The requester cannot approve their own request.'))
            department_manager = request.department_id.manager_id.user_id
            if department_manager and department_manager != self.env.user and not self.env.user.has_group(
                'voigt_hr_recruitment.group_voigt_recruitment_manager'
            ):
                raise UserError(self.env._('Department approval must be performed by the department manager.'))
            super(VoigtRecruitmentRequest, request).write({
                'state': 'to_director', 'department_approver_id': self.env.user.id,
                'department_approved_at': fields.Datetime.now(),
            })

    def action_approve_director(self):
        is_system_admin = self.env.user.has_group('base.group_system')
        for request in self:
            if request.state != 'to_director':
                raise UserError(self.env._('This request is not awaiting director approval.'))
            if not is_system_admin and (
                request.requester_id == self.env.user or request.department_approver_id == self.env.user
            ):
                raise UserError(self.env._('Director approval must be performed by a different user.'))
            super(VoigtRecruitmentRequest, request).write({
                'state': 'approved', 'director_approver_id': self.env.user.id,
                'director_approved_at': fields.Datetime.now(),
            })

    def action_reject(self):
        for request in self:
            if request.state not in ('to_approve', 'to_director'):
                raise UserError(self.env._('Only requests awaiting approval can be rejected.'))
            if not request.approval_comment:
                raise UserError(self.env._('Enter a reason for rejecting the request.'))
            super(VoigtRecruitmentRequest, request).write({'state': 'rejected'})

    def action_reset_to_draft(self):
        if not self.env.user.has_group('voigt_hr_recruitment.group_voigt_recruitment_manager'):
            raise UserError(self.env._('Only Voigt recruitment managers can reopen requests.'))
        for request in self:
            if request.state != 'rejected':
                raise UserError(self.env._('Only rejected requests can be reopened.'))
            super(VoigtRecruitmentRequest, request).write({
                'state': 'draft', 'department_approver_id': False, 'department_approved_at': False,
                'director_approver_id': False, 'director_approved_at': False,
            })
