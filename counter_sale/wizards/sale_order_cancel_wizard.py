from odoo import models


class SaleOrderCancel(models.TransientModel):
    _inherit = "sale.order.cancel"

    def action_reprocess(self):
        self.ensure_one()
        self = self.sudo()
        new_order = self.order_id.copy()
        new_order.rectified_order_id = self.order_id

        move_quantities = {}
        for picking in self.order_id.picking_ids.filtered(
            lambda pick: pick.state == "assigned"
        ):
            for move in picking.move_ids:
                move.rectified_product_uom_qty = move.quantity
                move.rectified_quantity = move.product_uom_qty
                move_quantities[move.product_id.id] = move.quantity

        for line in new_order.order_line:
            if line.product_id.id in move_quantities:
                line.product_uom_qty = move_quantities[line.product_id.id]

        self.order_id.with_context(disable_cancel_warning=True).action_cancel()

        for payment in self.order_id.payment_ids:
            if payment.state != "processed":
                payment.state = "cancel"

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self.order_id._name,
            "res_id": new_order.id,
            "target": "current",
        }

    def action_cancel(self):
        res = super(SaleOrderCancel, self).action_cancel()
        for payment in self.order_id.payment_ids:
            if payment.state != "processed":
                payment.state = "cancel"
            elif payment.state == "processed":
                payment.state = "cancel"
                payment.difference = -payment.amount
        return res
