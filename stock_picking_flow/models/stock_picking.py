from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    picker_user_id = fields.Many2one("res.users", string="Picker User", readonly=True)
    is_owner_picker_user = fields.Boolean(compute="_compute_is_owner_user")
    collection_state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("assigned", "Assigned"),
            ("confirmed", "Confirmed"),
            ("issue", "With Issue"),
        ],
        string="Collection Status",
        default="waiting",
        copy=False,
    )
    sale_person_id = fields.Many2one(
        "res.users",
        string="Sale Person",
        compute="_compute_sale_person_id",
    )

    purchase_person_id = fields.Many2one(
        "res.users",
        string="Purchase Person",
        compute="_compute_purchase_person_id",
    )
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

    @api.depends("origin")
    def _compute_purchase_person_id(self):
        for picking in self:
            purchase_order = self.env["purchase.order"].search(
                [("name", "=", picking.origin)]
            )
            if purchase_order:
                picking.purchase_person_id = purchase_order.user_id
            else:
                picking.purchase_person_id = False

    @api.depends("origin")
    def _compute_sale_person_id(self):
        for picking in self:
            sale_order = self.env["sale.order"].search([("name", "=", picking.origin)])
            if sale_order:
                picking.sale_person_id = sale_order.user_id
            else:
                picking.sale_person_id = False

    def _compute_is_owner_user(self):
        for picking in self:
            picking.is_owner_picker_user = picking.picker_user_id.id == self.env.user.id

    @api.model
    def get_states(self, state_type):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        field = self._fields.get(state_type, False)
        if not field:
            return []
        selection = field._description_selection(self.env)
        return [{"value": value, "label": label} for value, label in selection]

    @api.model
    def get_state_label(self, state_type, value):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        field = self._fields.get(state_type)
        if not field:
            return None

        selection = field._description_selection(self.env)
        return next((label for val, label in selection if val == value), None)

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
        if picking.collection_state != "waiting":
            raise ValidationError(
                _(
                    "Cannot assign picker: picking '%s' is not in waiting state.",
                    picking.display_name,
                )
            )
        picking.picker_user_id = user_id
        picking.collection_state = "assigned"
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "collection_state": picking.collection_state,
            "user_id": picking.picker_user_id.name,
        }

    def action_reserve_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.collection_state = "assigned"

    @api.model
    def get_picking(self, picking_id):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        picking = self.browse(picking_id)
        if not picking.exists():
            raise ValidationError(_("Picking not found."))
        move_lines = []

        for move in picking.move_ids_without_package:
            move_lines.append(
                {
                    "id": move.id,
                    "productId": {
                        "id": move.product_id.product_tmpl_id.id,
                        "qtyAvailable": move.product_id.qty_available,
                        "barcodes": move.product_id.product_tmpl_id.barcodes,
                        "name": move.product_id.product_tmpl_id.display_name,
                    },
                    "productUomQty": move.product_uom_qty,
                    "quantity": 0,
                    "internalLocationId": move.internal_location_id.display_name,
                }
            )
        return {
            "id": picking.id,
            "origin": picking.origin,
            "name": picking.name,
            "partner_id": picking.partner_id.name,
            "scheduled_date": picking.scheduled_date,
            "state": picking.state,
            "collection_state": picking.collection_state,
            "picker_user_id": picking.picker_user_id.name,
            "move_ids": move_lines,
            "confirmed_date": picking.confirmed_date,
            "date_done": picking.date_done,
            "terms_and_conditions": picking.terms_and_conditions,
            "responsible_person_id": picking.sale_person_id.name
            or picking.purchase_person_id.name,
        }

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
        if picking.collection_state != "assigned":
            raise ValidationError(
                _(
                    "Cannot confirm this picking:'%s' is not in assigned state.",
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
        picking.sudo().collection_state = "confirmed"
        return {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "collection_state": picking.collection_state,
            "user_id": picking.picker_user_id.name,
        }

    def action_confirm_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.sudo().collection_state = "confirmed"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("acc_number"):
                vals["picker_user_id"] = self.env.user.id
        return super(StockPicking, self).create(vals_list)


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_picking_default_values(self):
        res = super(ReturnPicking, self)._prepare_picking_default_values()
        res["collection_state"] = "waiting"
        res["user_id"] = False
        res["picker_user_id"] = False
        return res
