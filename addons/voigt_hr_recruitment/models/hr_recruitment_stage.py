from odoo import fields, models


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    voigt_gate = fields.Selection([
        ('none', 'Sem bloqueio Voigt'), ('screening', 'Exige avaliação RH aprovada'),
        ('technical', 'Exige entrevista técnica aprovada'), ('admission', 'Exige documentos e aptidão ocupacional'),
        ('offer', 'Exige aprovação RQ 077, documentos e aptidão ocupacional'),
    ], default='none', string='Controle de passagem Voigt')
