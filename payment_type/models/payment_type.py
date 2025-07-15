from odoo import fields, models


class PaymentType(models.Model):
    _name = "payment.type"
    _description = "Payments types in sales"

    name = fields.Char(required=True)
    is_credit = fields.Boolean(string="Use as credit", default=False)
