from odoo import fields, models


class VoigtApplicantAssessmentCriterion(models.Model):
    _name = 'voigt.applicant.assessment.criterion'
    _description = 'Voigt Applicant Assessment Criterion'
    _order = 'sequence, id'

    assessment_id = fields.Many2one('voigt.applicant.assessment', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    result = fields.Selection([
        ('pending', 'Pendente'), ('meets', 'Atende'), ('partial', 'Atende parcialmente'), ('not_meets', 'Não atende'),
    ], default='pending', required=True)
    notes = fields.Text()
