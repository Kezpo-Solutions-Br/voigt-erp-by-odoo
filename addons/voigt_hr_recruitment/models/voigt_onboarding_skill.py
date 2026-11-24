from odoo import fields, models


class VoigtOnboardingSkill(models.Model):
    _name = 'voigt.onboarding.skill'
    _description = 'Voigt RQ 006 Skill and Attitude Evaluation'
    _order = 'kind, sequence, id'

    onboarding_id = fields.Many2one('voigt.onboarding', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection([('skill', 'Habilidade'), ('attitude', 'Atitude')], required=True)
    name = fields.Char(required=True)
    rating = fields.Selection([
        ('0', '0 - Ruim'), ('1', '1 - Regular'), ('3', '3 - Bom'), ('5', '5 - Ótimo'),
    ])
    notes = fields.Text()
