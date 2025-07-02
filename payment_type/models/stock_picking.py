from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    paid = fields.Boolean(
        default=False,
    )

    invoice_number = fields.Char()

    def action_cancel(self):
        res = super().action_cancel()
        order = self.sale_id
        order.state = "cancel"
        return res

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            invoice = picking.sale_id._create_invoices()
            invoice.write({"payment_method": picking.payment_method.id})
            invoice.action_post()
            picking.invoice_number = invoice.number
        return res
