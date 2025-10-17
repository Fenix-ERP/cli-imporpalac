from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    confirmed_date = fields.Datetime(
        string="Date confirmed",
        readonly=True,
        copy=False,
    )

    def write(self, vals):
        res = super().write(vals)
        if "collection_state" in vals and vals["collection_state"] == "assigned":
            for picking in self:
                if not picking.confirmed_date:
                    picking.confirmed_date = fields.Datetime.now()
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)

        # Assign the location if it is an outgoing pick (sale).
        if (
            self.picking_id.picking_type_id.code == "outgoing"
            and self.sale_line_id
            and self.sale_line_id.internal_location_id
        ):
            vals["location_id"] = self.sale_line_id.internal_location_id.id

        return vals

    def _action_assign(self):
        super_result = super()._action_assign()

        for move in self:
            if (
                move.picking_id.picking_type_id.code == "outgoing"
                and move.sale_line_id
                and move.sale_line_id.internal_location_id
                and move.move_line_ids
            ):
                for move_line in move.move_line_ids:
                    if move_line.location_id != move.sale_line_id.internal_location_id:
                        move_line.location_id = move.sale_line_id.internal_location_id

        return super_result