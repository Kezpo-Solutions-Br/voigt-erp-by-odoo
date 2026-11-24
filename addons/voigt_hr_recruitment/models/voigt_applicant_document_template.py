from odoo import fields, models


class VoigtApplicantDocumentTemplate(models.Model):
    _name = 'voigt.applicant.document.template'
    _description = 'Voigt Admission Checklist Template'
    _order = 'profile, sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    profile = fields.Selection([
        ('all', 'Todos os perfis'), ('administrative', 'Administrativo'),
        ('production_rebarbacao', 'Auxiliar de Produção - Rebarbação'),
        ('production_moldagem', 'Auxiliar de Produção - Moldagem'), ('mechanic', 'Mecânico de Manutenção'),
        ('other', 'Outro'),
    ], default='all', required=True)
    required = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
