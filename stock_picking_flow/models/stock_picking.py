from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"
    picker_user_id = fields.Many2one("res.users", string="Picker User", readonly=True)
    is_owner_picker_user = fields.Boolean(compute="_compute_is_owner_user")

    def _compute_is_owner_user(self):
        for picking in self:
            picking.is_owner_picker_user = picking.picker_user_id.id == self.env.user.id

    def action_reserve_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.state = "confirmed"

    def action_confirm_picking(self):
        for picking in self:
            picking.user_id = self.env.user.id
            picking.state = "assigned"

    @api.model
    def create(self, vals):
        vals["picker_user_id"] = self.env.user.id
        record = super(StockPicking, self).create(vals)
        return record
