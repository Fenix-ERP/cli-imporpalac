from datetime import timedelta

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    elapsed_time = fields.Char(
        compute="_compute_elapsed_time",
        store=True,
        help="Time from order confirmation to delivery",
    )
    picking_elapsed_time = fields.Char(
        compute="_compute_picking_elapsed_time",
        store=True,
        help="Time from picking reservation to delivery",
    )
    dispatcher_id = fields.Many2one(
        "res.users",
        string="Dispatcher",
        compute="_compute_dispatcher",
        store=True,
        help="User who performed the dispatch",
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

    # -------------------- Dispatcher --------------------
    @api.depends("picking_ids.user_id", "picking_ids.state", "picking_ids.date_done")
    def _compute_dispatcher(self):
        for order in self:
            done_pickings = order.picking_ids.filtered(
                lambda p: p.state == "done" and p.date_done
            ).sorted("date_done", reverse=True)
            order.dispatcher_id = done_pickings[0].user_id if done_pickings else False

    # -------------------- Timer de Orden --------------------
    @api.depends("date_order", "picking_ids.date_done")
    def _compute_elapsed_time(self):
        for order in self:
            done_dates = order.picking_ids.filtered(lambda p: p.date_done).mapped(
                "date_done"
            )
            if not done_dates:
                order.elapsed_time = "Without picking"
                continue

            last_done_date = max(done_dates)
            if not order.date_order:
                order.elapsed_time = "Without order date"
                continue

            delta = last_done_date - order.date_order
            order.elapsed_time = self._format_delta(delta)

    # -------------------- Timer de Picking --------------------
    @api.depends(
        "picking_ids.confirmed_date", "picking_ids.date_done", "picking_ids.state"
    )
    def _compute_picking_elapsed_time(self):
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.confirmed_date and p.date_done and p.state == "done"
            )
            if not pickings:
                order.picking_elapsed_time = "Without picking"
                continue

            first_confirmed = min(pickings.mapped("confirmed_date"))
            last_done = max(pickings.mapped("date_done"))
            delta = last_done - first_confirmed
            order.picking_elapsed_time = self._format_delta(delta)

    # -------------------- Delivery Status --------------------
    @api.depends("picking_ids.state")
    def _compute_delivery_status(self):
        for order in self:
            if not order.picking_ids:
                order.delivery_status = False
            else:
                states = order.picking_ids.mapped("state")

                if any(s == "waiting" for s in states):
                    order.delivery_status = "waiting"  # Rojo
                elif any(s == "confirmed" for s in states):
                    order.delivery_status = "picking"  # Amarillo
                elif any(s == "assigned" for s in states):
                    order.delivery_status = "to_deliver"  # Gris
                elif all(s == "done" for s in states):
                    order.delivery_status = "delivered"  # Verde
                else:
                    order.delivery_status = False

    # -------------------- Helper --------------------
    def _format_delta(self, delta: timedelta):
        days = delta.days
        seconds = delta.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} días")
        if hours > 0:
            parts.append(f"{hours} horas")
        if minutes > 0 or not parts:
            parts.append(f"{minutes} minutos")

        return ", ".join(parts)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_done(self):
        res = super(StockPicking, self).action_done()
        sale_orders = self.mapped("sale_id")
        sale_orders._compute_dispatcher()
        sale_orders._compute_elapsed_time()
        sale_orders._compute_picking_elapsed_time()
        sale_orders._compute_delivery_status()
        return res
