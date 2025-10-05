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
        """
        Esta es la mejor opción - se ejecuta cuando se crean las operaciones de stock
        """
        vals = super(StockMove, self)._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )

        # Asignar la ubicación específica de la línea de venta
        if self.sale_line_id and self.sale_line_id.internal_location_id:
            vals["location_id"] = self.sale_line_id.internal_location_id.id

        return vals

    def _action_assign(self):
        """
        Como respaldo, asegurar que las operaciones existentes tengan la ubicación correcta
        """
        super_result = super(StockMove, self)._action_assign()

        # Verificar y corregir ubicaciones después de la asignación
        for move in self:
            if (
                move.sale_line_id
                and move.sale_line_id.internal_location_id
                and move.move_line_ids
            ):

                for move_line in move.move_line_ids:
                    if move_line.location_id != move.sale_line_id.internal_location_id:
                        move_line.location_id = move.sale_line_id.internal_location_id

        return super_result
