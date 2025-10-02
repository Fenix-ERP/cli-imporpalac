from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            active_users = (
                self.env["res.users"]
                .search([("active", "=", True)])
                .mapped("partner_id")
            )
            if active_users:
                for record in self:
                    notifications = [
                        (
                            partner,
                            "tree_view_refresh",
                            {"presence_status": record.state},
                        )
                        for partner in active_users
                    ]
                    self.env["bus.bus"]._sendmany(notifications)

        return res
