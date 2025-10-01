from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    picker_user_id = fields.Many2one("res.users", string="Picker User", readonly=True)
    is_owner_picker_user = fields.Boolean(compute="_compute_is_owner_user")
    issue_reported = fields.Boolean(default=False)

    def _compute_is_owner_user(self):
        for picking in self:
            picking.is_owner_picker_user = picking.picker_user_id.id == self.env.user.id

    @api.model
    def get_states(self):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        allowed_states = ["draft", "waiting", "confirmed", "assigned", "done", "cancel"]
        selection = dict(self._fields["state"]._description_selection(self.env))
        states = allowed_states or selection.keys()
        return [
            {"value": val, "label": selection[val]}
            for val in states
            if val in selection
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
        picking.sudo().confirmed_date = fields.Datetime.now()
        picking.move_ids.sudo().write({"state": "confirmed"})
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "user_id": picking.picker_user_id.name,
        }

    def action_reserve_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.sudo().confirmed_date = fields.Datetime.now()
            picking.move_ids.sudo().write({"state": "confirmed"})

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
            move_line = picking.move_ids_without_package.filtered(
                lambda ml: ml.id == line_id
            )
            if not move_line:
                raise ValidationError(_("Stock Move Line not found."))
            qty = line_data.get("quantity", 0)
            issue = line_data.get("issue", False)
            has_issue = False
            issue_qty = 0
            issue_type = False
            issue_notes = False
            if issue:
                has_issue = True
                issue_qty = issue.get("quantity", 0)
                issue_type = issue.get("type", False)
                issue_notes = issue.get("notes", [])
                issue_notes = "\n".join(issue_notes)

            move_line.sudo().write(
                {
                    "quantity": qty,
                    "has_issue": has_issue,
                    "issue_qty": issue_qty,
                    "issue_type": issue_type,
                    "issue_notes": issue_notes,
                }
            )
        picking.picker_user_id = user_id
        picking.move_ids.sudo().write({"state": "assigned"})
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "user_id": picking.picker_user_id.name,
        }

    def action_confirm_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.move_ids.sudo().write({"state": "assigned"})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("acc_number"):
                vals["picker_user_id"] = self.env.user.id
        return super(StockPicking, self).create(vals_list)
