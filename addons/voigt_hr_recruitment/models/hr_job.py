from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    voigt_profile = fields.Selection([
        ('administrative', 'Administrativo'), ('production_rebarbacao', 'Auxiliar de Produção - Rebarbação'),
        ('production_moldagem', 'Auxiliar de Produção - Moldagem'),
        ('mechanic', 'Mecânico de Manutenção'), ('other', 'Outro'),
    ], string='Perfil do processo Voigt', default='other', tracking=True)
    voigt_request_id = fields.Many2one('voigt.recruitment.request', string='Solicitação RQ 077', check_company=True, tracking=True)
