from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        default=lambda self: self.env.ref(
            "payment_type.payment_type_cash", raise_if_not_found=False
        ),
    )

    phone = fields.Char(required=True)

    property_payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Términos de pago",
        default=lambda self: self.env.ref(
            "account.account_payment_term_immediate", raise_if_not_found=False
        ),
    )

    street = fields.Char(required=True)
