from odoo import models


class SaleOrderCancel(models.TransientModel):
    _inherit = "sale.order.cancel"

    def action_reprocess(self):
        self.ensure_one()
        new_order = self.order_id.copy()
        new_order.rectified_order_id = self.order_id
        for picking in self.order_id.picking_ids.filtered(
            lambda pick: pick.state == "assigned"
        ):
            for move in picking.move_ids:
                move.rectified_product_uom_qty = move.product_uom_qty
                move.rectified_quantity = move.quantity
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

    def action_send_mail_and_cancel(self):
        res = super(SaleOrderCancel, self).action_send_mail_and_cancel()
        for payment in self.order_id.payment_ids:
            if payment.state != "processed":
                payment.state = "cancel"
        return res
