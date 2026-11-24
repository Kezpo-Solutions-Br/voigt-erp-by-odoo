from odoo import fields, models


class VoigtOnboardingSkillTemplate(models.Model):
    _name = 'voigt.onboarding.skill.template'
    _description = 'Voigt RQ 006 Skill and Attitude Template'
    _order = 'kind, sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection([('skill', 'Habilidade'), ('attitude', 'Atitude')], required=True)
    active = fields.Boolean(default=True)
