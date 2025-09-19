from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    picker_user_id = fields.Many2one("res.users", string="Picker User", readonly=True)
    is_owner_picker_user = fields.Boolean(compute="_compute_is_owner_user")

    def _compute_is_owner_user(self):
        for picking in self:
            picking.is_owner_picker_user = picking.picker_user_id.id == self.env.user.id

    @api.model
    def get_states(self):
        return [
            {"value": value, "label": _(label)}
            for value, label in self._fields["state"].selection
        ]

    @api.model
    def action_assign_picker(self, data):
        picking_id = data.get("picking_id")
        user_id = data.get("user_id")
        picking = self.browse(picking_id)
        if not picking.exists():
            raise ValidationError(_("Picking not found."))
        if picking.picker_user_id:
            raise ValidationError(
                _(
                    "This picking is already assigned to %s ",
                    picking.picker_user_id.name,
                )
            )
        if picking.state not in ["draft", "waiting"]:
            raise ValidationError(
                _(
                    "Cannot assign picker: picking '%s' is not in waiting state.",
                    picking.display_name,
                )
            )
        picking.picker_user_id = user_id
        picking.state = "confirmed"
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "user_id": picking.picker_user_id.name,
        }

    def action_reserve_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.state = "confirmed"

    @api.model
    def action_confirm_by_picker(self, data):
        picking_data = data.get("picking_data")
        picking_id = picking_data.get("pickingId", False)
        picking_moves = picking_data.get("moveLines", [])
        user_id = data.get("user_id")
        picking = self.browse(picking_id)
        if not picking.exists():
            raise ValidationError(_("Picking not found."))
        if picking.picker_user_id and picking.picker_user_id.id != user_id:
            raise ValidationError(
                _(
                    "This picking is assigned to %s, you cannot confirm it",
                    picking.picker_user_id.name,
                )
            )
        if picking.state != "confirmed":
            raise ValidationError(
                _(
                    "Cannot confirm this picking:'%s' is not in confirmed state.",
                    picking.display_name,
                )
            )
        for line_data in picking_moves:
            line_id = line_data.get("id", False)
            qty = line_data.get("quantity", 0)
            move_line = picking.move_line_ids.filtered(lambda ml: ml.id == line_id)
            if not move_line:
                raise ValidationError(_("Stock Move Line not found."))
            move_line.quantity = qty
        picking.picker_user_id = user_id
        picking.state = "assigned"
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "user_id": picking.picker_user_id.name,
        }

    def action_confirm_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.state = "assigned"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("acc_number"):
                vals["picker_user_id"] = self.env.user.id
        return super(StockPicking, self).create(vals_list)
