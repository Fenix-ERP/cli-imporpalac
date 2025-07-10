from datetime import datetime

from odoo import api, fields, models


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
    hour_register_rectified = fields.Datetime(string="Rectified Payment Time")

    amount_total = fields.Monetary(
        string="Total Amount", compute="_compute_amount", currency_field="currency_id"
    )
    rectified_amount = fields.Monetary()

    difference = fields.Monetary(compute="_compute_difference")

    journal_id = fields.Many2one("account.journal", string="Payment Journal")

    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    state = fields.Selection(
        [
            ("draft", "Pending"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    @api.depends("order_id")
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = rec.order_id.amount_total

    @api.depends("amount_total", "rectified_amount", "state")
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.amount_total - rec.rectified_amount

    def action_open_payment_wizard(self):
        for payment in self:
            payment.state = "paid"


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

    def action_cancel_payment(self):
        res = super(SaleOrder, self).action_cancel_payment()
        for payment in self.payment_ids:
            if payment.state != "paid":
                payment.state = "cancelled"
        return res

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.env["sale.order.payment"].create(
            {
                "order_id": self.id,
                "client_id": self.partner_id.id,
                "date_order": self.date_order,
                "hour_register": datetime.now(),
                "amount_total": self.amount_total,
                "journal_id": self.warehouse_id.journal_payment_id.id,
                "payment_method": self.payment_method.id,
                "state": "draft",
            }
        )
        return res
