from odoo import fields, models


class VoigtAssessmentCriterionTemplate(models.Model):
    _name = 'voigt.assessment.criterion.template'
    _description = 'Voigt Assessment Criterion Template'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    profile = fields.Selection([
        ('administrative', 'Administrativo'), ('production_rebarbacao', 'Auxiliar de Produção - Rebarbação'),
        ('production_moldagem', 'Auxiliar de Produção - Moldagem'),
        ('mechanic', 'Mecânico de Manutenção'), ('other', 'Outro'),
    ], required=True)
    assessment_type = fields.Selection([
        ('hr', 'Entrevista RH'), ('technical', 'Entrevista técnica'),
        ('director', 'Entrevista diretoria'), ('probation', 'Avaliação de experiência'),
    ], required=True, default='technical')
    active = fields.Boolean(default=True)
