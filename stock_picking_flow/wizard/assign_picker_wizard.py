from odoo import fields, models


class AssignPickerWizard(models.TransientModel):
    _name = "assign.picker.wizard"
    _description = "Assign Picker Wizard"

    picker_id = fields.Many2one(
        "res.users",
        string="Picker",
        required=True,
    )

    def action_assign(self):
        active_ids = self.env.context.get("active_ids")
        pickings = self.env["stock.picking"].browse(active_ids)
        allowed_pickings = pickings.filtered(lambda p: p.collection_state == "waiting")
        allowed_pickings.write(
            {"picker_user_id": self.picker_id.id, "collection_state": "assigned"}
        )
