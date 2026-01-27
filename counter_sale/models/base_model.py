from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ("state", "collection_state")):
            allowed_models_param = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("refresh_tree_view.bus_allowed_models", "")
            )
            allowed_models = [
                m.strip() for m in allowed_models_param.split(",") if m.strip()
            ]
            if self._name in allowed_models:
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
