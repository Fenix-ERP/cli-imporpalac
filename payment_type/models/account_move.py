from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )
