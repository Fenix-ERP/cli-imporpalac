from odoo import _, fields, models
from odoo.exceptions import ValidationError


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
        for picking in related_pickings:
            picking.state = "waiting"
        for old_picking, new_picking in zip(
            rectified_related_pickings, related_pickings
        ):
            for old_move in old_picking.move_ids:
                new_move = new_picking.move_ids.filtered(
                    lambda m: m.product_id == old_move.product_id
                )
                if new_move:
                    new_move.rectified_product_uom_qty = (
                        old_move.rectified_product_uom_qty
                    )
                    new_move.rectified_quantity = old_move.rectified_quantity
        if not self.warehouse_id.journal_payment_id:
            raise ValidationError(
                _(
                    "There is no payment journal in warehouse %s, please assign it.",
                    self.warehouse_id.display_name,
                )
            )
        self.env["sale.order.payment"].create(
            {
                "client_id": self.partner_id.id,
                "order_id": self.id,
                "date_order": self.date_order,
                "amount": self.amount_total,
                "rectified_order_id": self.rectified_order_id.id,
                "rectified_date_order": self.rectified_order_id.date_order,
                "rectified_amount": self.rectified_order_id.amount_total,
                "journal_id": self.warehouse_id.journal_payment_id.id,
                "payment_method": self.payment_method.id,
                "state": "draft",
            }
        )
        return res

    def action_cancel(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_cancel()
        for payment in self.payment_ids:
            if payment.state != "processed":
                payment.state = "cancel"
        return res
