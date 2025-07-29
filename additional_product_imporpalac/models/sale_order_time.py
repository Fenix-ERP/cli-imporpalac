from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = 'Sale order'

    elapsed_time = fields.Char(
        string="Elapsed Time",
        compute='_compute_elapsed_time',
        store=True,
        help="Time between order creation and dispatch"
    )
    dispatcher_id = fields.Many2one(
        'res.users',
        string="Despachador",
        compute='_compute_dispatcher',
        store=True,
        help="Usuario que realizó el despacho"
    )
    @api.depends('picking_ids.user_id')
    def _compute_dispatcher(self):
        for order in self:
            # Tomamos el último picking completado
            done_pickings = order.picking_ids.filtered(lambda p: p.date_done)
            if done_pickings:
                # Ordenamos por fecha de done y tomamos el más reciente
                last_picking = done_pickings.sorted(key=lambda p: p.date_done, reverse=True)[0]
                order.dispatcher_id = last_picking.user_id
            else:
                order.dispatcher_id = False
    
    @api.depends('create_date', 'date_order', 'picking_ids.date_done')
    def _compute_elapsed_time(self):
        for order in self:
            if not order.picking_ids:
                order.elapsed_time = "No dispatch"
                continue

            done_dates = order.picking_ids.filtered(
                lambda p: p.date_done
            ).mapped('date_done')
            
            if not done_dates:
                order.elapsed_time = "No dispatch completed"
                continue
                
            last_done_date = max(done_dates)
            create_date = order.create_date or order.date_order
            
            if not create_date:
                order.elapsed_time = "Date created not available"
                continue
                
            # We calculate the time difference
            delta = last_done_date - create_date

            # We convert to days, hours, minutes
            days = delta.days
            seconds = delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60

            # We format the result
            time_parts = []
            if days > 0:
                time_parts.append(f"{days} días")
            if hours > 0:
                time_parts.append(f"{hours} horas")
            if minutes > 0 or not time_parts:
                time_parts.append(f"{minutes} minutos")
                
            order.elapsed_time = ", ".join(time_parts)