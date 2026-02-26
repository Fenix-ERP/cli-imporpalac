from odoo import fields, models


class AssignUserWizard(models.TransientModel):
    _name = "assign.user.wizard"
    _description = "Assign User Wizard"

    assign_type = fields.Selection(
        [("picker", "Picker"), ("driver", "Driver")],
        default=lambda self: self.env.context.get("assign_type"),
    )
    picker_id = fields.Many2one(
        "res.users",
        string="User",
    )
    driver_id = fields.Many2one(
        "res.users",
        string="User",
    )

    def action_assign_picker(self):
        active_ids = self.env.context.get("active_ids")
        pickings = self.env["stock.picking"].browse(active_ids)
        allowed_pickings = pickings.filtered(lambda p: p.collection_state == "waiting")
        allowed_pickings.write(
            {"picker_user_id": self.picker_id.id, "collection_state": "assigned"}
        )

    def action_assign_driver(self):
        active_ids = self.env.context.get("active_ids")
        pickings = self.env["stock.picking"].browse(active_ids)
        allowed_pickings = pickings.filtered(
            lambda p: p.state not in ["done", "cancel"]
        )
        allowed_pickings.write({"driver_user_id": self.driver_id.id})
