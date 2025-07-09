from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    state = fields.Selection(
        selection_add=[("approved", "Approved")],
    )

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

    def action_approve(self):
        if self.payment_method.name != "Crédito":
            raise ValidationError(
                _(
                    "No puedes aprobar este picking porque su método de pago debe estar Credito."
                )
            )
        self.state = "approved"
        order = self.sale_id
        invoice = order._create_invoices()
        invoice.payment_method = self.payment_method

    def action_cancel(self):
        res = super().action_cancel()
        order = self.sale_id
        order.state = "cancel"
        return res

    def button_validate(self):

        res = super(StockPicking, self).button_validate()

        if res == True:
            for picking in self:
                sale_order = picking.sale_id
                if sale_order and not picking.return_id:
                    invoice = picking.sale_id._create_invoices()
                    invoice.write({"payment_method": picking.payment_method.id})
                    invoice.action_post()
                    picking.invoice_number = invoice.name
        return res
