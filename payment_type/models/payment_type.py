from odoo import fields, models


class PaymentType(models.Model):
    _name = "payment.type"
    _description = "Payments types in sales"

    name = fields.Char(string="Name", required=True)