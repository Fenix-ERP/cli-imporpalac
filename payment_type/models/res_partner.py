from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
    )