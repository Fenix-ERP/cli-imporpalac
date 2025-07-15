from datetime import datetime

from odoo import _, api, fields, models


class SaleOrderPayment(models.Model):
    _name = "sale.order.payment"
    _description = "Sale Order Payment"

    name = fields.Char(
        string="Reference",
        default=lambda self: self.env["ir.sequence"].next_by_code("sale.order.payment"),
    )

    client_id = fields.Many2one(
        related="order_id.partner_id", string="Client", store=True
    )

    order_id = fields.Many2one("sale.order", string="Sale Order")
    rectified_order_id = fields.Many2one("sale.order", string="Rectified Sale Order")

    date_order = fields.Date(string="Order Date")
    rectified_date_order = fields.Date(string="Rectified Order Date")

    hour_register = fields.Datetime(string="Payment Register Time")

    amount = fields.Monetary(
        compute="_compute_amount", currency_field="currency_id", store=True
    )
    rectified_amount = fields.Monetary()

    difference = fields.Monetary(compute="_compute_difference")

    journal_id = fields.Many2one("account.journal", string="Payment Journal")
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        readonly=False,
        store=True,
        copy=False,
        compute="_compute_payment_method_line_id",
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )
    available_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line", compute="_compute_payment_method_line_fields"
    )

    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    state = fields.Selection(
        [
            ("draft", "Pending"),
            ("processed", "Processed"),
            ("cancel", "Cancel"),
        ],
        default="draft",
    )

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
        default=False,
    )

    @api.depends("journal_id")
    def _compute_payment_method_line_fields(self):
        for rec in self:
            rec.available_payment_method_line_ids = (
                rec.journal_id._get_available_payment_method_lines("inbound")
            )

    @api.depends("available_payment_method_line_ids")
    def _compute_payment_method_line_id(self):
        for rec in self:
            available_payment_method_lines = rec.available_payment_method_line_ids
            if rec.payment_method_line_id in available_payment_method_lines:
                rec.payment_method_line_id = rec.payment_method_line_id
            elif available_payment_method_lines:
                rec.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                rec.payment_method_line_id = False

    @api.depends("order_id")
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.order_id.amount_total

    @api.depends("amount", "rectified_amount", "state")
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.amount - rec.rectified_amount

    def process_payment(self):
        for payment in self:
            skip_open = self.env.context.get("skip_open_payment_method_wizzard", False)
            if not skip_open:
                method_lines = payment.journal_id.inbound_payment_method_line_ids
                if method_lines:
                    if len(method_lines) > 1:
                        domain = self.available_payment_method_line_ids.ids
                        return {
                            "name": _("Confirm Payment Method"),
                            "type": "ir.actions.act_window",
                            "view_type": "form",
                            "view_mode": "form",
                            "res_model": "sale.order.payment.method.wizard",
                            "view_id": self.env.ref(
                                "sale_order_payment.sale_order_payment_method_view_form"
                            ).id,
                            "target": "new",
                            "context": {
                                "default_sale_order_payment_id": self.id,
                                "default_balance": self.difference,
                                "default_payment_method_domain": f"[('id', 'in', {domain})]"
                                "",
                            },
                        }
            payment.state = "processed"
            payment.hour_register = datetime.now()
            for picking in payment.order_id.picking_ids:
                picking.payment_state = "paid"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_ids = fields.Many2one(
        "sale.order.payment", string="Payments Related", compute="_compute_payment_ids"
    )

    payment_count = fields.Integer(
        string="Number of Payments", compute="_compute_payment_ids"
    )

    def _compute_payment_ids(self):
        for order in self:
            payments = self.env["sale.order.payment"].search(
                [("order_id", "=", order.id)]
            )
            order.payment_ids = payments
            order.payment_count = len(payments)

    def action_open_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Sale Payments",
            "res_model": "sale.order.payment",
            "view_mode": "tree",
            "domain": [("order_id", "=", self.id)],
            "context": {"default_order_id": self.id},
        }
