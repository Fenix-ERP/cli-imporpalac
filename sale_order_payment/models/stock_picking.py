from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_state = fields.Selection(
        [
            ("not_paid", "Not Paid"),
            ("paid", "Paid"),
            ("credit", "Credit"),
        ],
        string="Payment Status",
        default="not_paid",
    )

    delivery_status = fields.Selection(
        [
            ("waiting", "En Espera"),
            ("picking", "Picking"),
            ("to_deliver", "Por Entregar"),
            ("delivered", "Entregado"),
        ],
        compute="_compute_delivery_status",
        store=True,
    )

    @api.depends("origin")
    def _compute_delivery_status(self):
        for picking in self:
            sale_order = self.env["sale.order"].search([("name", "=", picking.origin)])
            if sale_order:
                picking.delivery_status = sale_order.delivery_status
