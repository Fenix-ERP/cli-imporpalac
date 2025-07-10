from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
        required=True,
    )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ["done", "cancel"]
            )
            for picking in pickings:
                picking.payment_method = order.payment_method
        return res

    def _create_invoices(self, grouped=False, final=False):
        """
        Sobrescritura del método para asignar automáticamente el diario en la factura
        dependiendo del almacén de la entrega.
        """
        invoices = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final)

        for invoice in invoices:
            # Obtener el picking relacionado con la orden
            related_pickings = self.picking_ids.filtered(lambda p: p.state == "done")
            if related_pickings:
                warehouse = related_pickings[0].picking_type_id.warehouse_id
                if warehouse and warehouse.journal_id:
                    invoice.journal_id = warehouse.journal_id
        return invoices


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    image_1920 = fields.Image(related="product_id.image_1920", readonly=True)
