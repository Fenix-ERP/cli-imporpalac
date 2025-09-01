from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        default=lambda self: self.env.ref(
            "payment_type.payment_type_cash", raise_if_not_found=False
        ),
    )

    credit = fields.Monetary(
        related="partner_id.credit",
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.payment_method = self.partner_id.payment_method

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            identifier = order.partner_id.is_end_consumer
            if identifier:
                if order.amount_total > order.company_id.max_amount_final_consumer:
                    raise ValidationError(
                        _("Exceeds the maximum value for end consumers")
                    )
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ["done", "cancel"]
            )
            for picking in pickings:
                picking.payment_method = order.payment_method
        return res

    def _create_invoices(self, grouped=False, final=False):
        invoices = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final)

        for invoice in invoices:
            related_pickings = self.picking_ids.filtered(lambda p: p.state == "done")
            if related_pickings:
                warehouse = related_pickings[0].picking_type_id.warehouse_id
                if warehouse and warehouse.journal_id:
                    invoice.journal_id = warehouse.journal_id
        return invoices


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    image_1920 = fields.Image(related="product_id.image_1920", readonly=True)
