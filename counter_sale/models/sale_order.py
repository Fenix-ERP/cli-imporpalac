from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    rectified_order_id = fields.Many2one(
        "sale.order", string="Rectified Sale Order", readonly=True
    )

    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        # Enviar a imprimir a caja
        # Enviar a imprimir a bodega
        rectified_related_pickings = self.rectified_order_id.picking_ids
        related_pickings = self.picking_ids
        for old_picking, new_picking in zip(
            rectified_related_pickings, related_pickings
        ):
            new_picking.is_rectified = True
            for old_move in old_picking.move_ids:
                new_move = new_picking.move_ids.filtered(
                    lambda m: m.product_id == old_move.product_id
                )
                if new_move:
                    new_move.rectified_product_uom_qty = (
                        old_move.rectified_product_uom_qty
                    )
                    new_move.rectified_quantity = old_move.rectified_quantity
        journal_payment_id = self.warehouse_id.payment_method_ids.filtered(
            lambda line: line.payment_type_id.id == self.payment_method.id
        ).journal_payment_id
        if not journal_payment_id and not self.payment_method.is_credit:
            raise ValidationError(
                _(
                    "There is no payment journal in warehouse %s, please assign it.",
                    self.warehouse_id.display_name,
                )
            )
        if not self.payment_method.is_credit:
            rectified_amount = 0
            if self.rectified_order_id:
                sale_order_payment = self.env["sale.order.payment"].search(
                    [("order_id", "=", self.rectified_order_id.id)]
                )
                if sale_order_payment.state == "cancel":
                    rectified_amount = 0
                else:
                    rectified_amount = self.rectified_order_id.amount_total
            self.env["sale.order.payment"].create(
                {
                    "client_id": self.partner_id.id,
                    "order_id": self.id,
                    "date_order": self.date_order,
                    "amount": self.amount_total,
                    "rectified_order_id": self.rectified_order_id.id,
                    "rectified_date_order": self.rectified_order_id.date_order,
                    "rectified_amount": rectified_amount,
                    "journal_id": journal_payment_id.id,
                    "payment_method": self.payment_method.id,
                    "state": "draft",
                    "company_id": self.company_id.id,
                }
            )
        else:
            for picking in related_pickings:
                picking.payment_state = "credit"
        return res

    def action_cancel(self):
        self.ensure_one()
        if self.invoice_count > 0:
            raise UserError(
                _("This order already has an invoice assigned and cannot be cancelled.")
            )
        res = super(SaleOrder, self).action_cancel()
        for payment in self.payment_ids:
            if payment.state != "processed":
                payment.state = "cancel"
        return res
