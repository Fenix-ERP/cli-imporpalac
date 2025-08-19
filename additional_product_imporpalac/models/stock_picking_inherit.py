from odoo import api, fields, models
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    confirmed_date = fields.Datetime(
        string="Date confirmed",
        readonly=True,
        copy=False,
    )

    def write(self, vals):
        old_states = {picking.id: picking.state for picking in self}
        res = super().write(vals)

        if "state" in vals:
            for picking in self:
                old_state = old_states.get(picking.id)
                new_state = picking.state
                if old_state == "waiting" and new_state == "confirmed":
                    picking.confirmed_date = fields.Datetime.now()

        return res
