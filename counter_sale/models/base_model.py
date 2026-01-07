from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ("state", "collection_state")):
            bus_message = {
                "params": self.env.context.get("params", {}),
            }
            channel = "refresh_tree_view_channel"
            self.env["bus.bus"]._sendone(
                channel,
                "refresh_tree_view.notify",
                bus_message,
            )

        return res
