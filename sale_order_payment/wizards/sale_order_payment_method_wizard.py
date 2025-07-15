from odoo import fields, models


class SaleOrderPaymentMethod(models.TransientModel):
    _name = "sale.order.payment.method.wizard"
    _description = "Sale Order Payment Method Wizard"

    sale_order_payment_id = fields.Many2one(
        "sale.order.payment", string="Sale Order Payment"
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        readonly=False,
        copy=False,
        domain="payment_method_domain",
    )
    payment_method_domain = fields.Char()
    balance = fields.Monetary(readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency")

    def action_confirm(self):
        self.ensure_one()
        self.sale_order_payment_id.payment_method_line_id = self.payment_method_line_id
        return self.with_context(
            skip_open_payment_method_wizzard=True
        ).sale_order_payment_id.process_payment()
