from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    state = fields.Selection(
        selection_add=[("approved", "Approved")],
    )

    paid = fields.Boolean(
        default=False,
    )

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
        for picking in self:
            if picking.payment_method.name == "Crédito" and picking.state != "approved":
                raise ValidationError(
                    _(
                        "No puedes validar este picking porque su método de pago es Credito. y debe estar en aprobada"
                    )
                )

        return super(StockPicking, self).button_validate()
