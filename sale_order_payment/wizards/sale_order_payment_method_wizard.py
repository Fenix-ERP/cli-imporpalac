from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrderPaymentMethod(models.TransientModel):
    _name = "sale.order.payment.method.wizard"
    _description = "Sale Order Payment Method Wizard"

    sale_order_payment_id = fields.Many2one(
        "sale.order.payment", string="Sale Order Payment"
    )
    sale_order_payment_method_code = fields.Char(
        string="Payment method",
        related="sale_order_payment_id.payment_method.code",
        readonly=True,
    )
    is_mixed_payment = fields.Boolean(
        related="sale_order_payment_id.is_mixed_payment",
        readonly=True,
    )
    reference = fields.Char()
    card_id = fields.Many2one("account.card", string="Card Used")
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        readonly=False,
        copy=False,
        domain="payment_method_domain",
    )
    payment_method_domain = fields.Char()
    balance = fields.Monetary(readonly=True)
    method_line_ids = fields.One2many(
        "sale.order.payment.method.line.wizard",
        "wizzard_id",
        string="Method lines",
        copy=True,
    )
    currency_id = fields.Many2one("res.currency", string="Currency")

    @api.constrains("method_line_ids", "balance")
    def _check_total_amount(self):
        for wizard in self:
            total = sum(line.amount for line in wizard.method_line_ids)
            if not float_compare(total, wizard.balance, precision_digits=2) == 0:
                raise ValidationError(
                    _(
                        "The total amount of payment lines (%(total).2f) must be exactly"
                        " equal to the total balance (%(amount).2f).",
                        total=total,
                        amount=wizard.balance,
                    )
                )

    def action_confirm(self):
        self.ensure_one()
        self.sale_order_payment_id.reference = self.reference
        for line in self.method_line_ids:
            self.env["sale.order.payment.line"].create(
                {
                    "payment_id": self.sale_order_payment_id.id,
                    "journal_id": line.journal_id.id,
                    "payment_method_line_id": line.payment_method_line_id.id,
                    "amount": line.amount,
                    "card_id": line.card_id.id,
                }
            )
        return self.with_context(
            skip_open_payment_method_wizzard=True
        ).sale_order_payment_id.process_payment()


class SaleOrderPaymentMethodLine(models.TransientModel):
    _name = "sale.order.payment.method.line.wizard"
    _description = "Sale Order Payment Method Line Wizard"
    wizzard_id = fields.Many2one(
        comodel_name="sale.order.payment.method.wizard",
        required=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
        copy=True,
    )
    sale_order_payment_method_code = fields.Char(
        string="Payment method",
        related="wizzard_id.sale_order_payment_method_code",
        readonly=True,
    )

    def _get_journal_domain(self):
        if self.sale_order_payment_method_code == "credit_card":
            return [("type", "in", ["bank", "cash"]), ("is_card_journal", "=", True)]
        else:
            return [("type", "in", ["bank", "cash"]), ("is_card_journal", "=", False)]

    journal_id = fields.Many2one(
        "account.journal", string="Journal", required=True, domain=_get_journal_domain
    )
    available_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line", compute="_compute_payment_method_line_fields"
    )

    @api.depends("journal_id")
    def _compute_payment_method_line_fields(self):
        for rec in self:
            rec.available_payment_method_line_ids = (
                rec.journal_id._get_available_payment_method_lines("inbound")
            )

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        readonly=False,
        required=True,
        copy=False,
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )
    card_id = fields.Many2one(
        "account.card",
        string="Card Used",
    )
    amount = fields.Monetary(required=True, default=0)
    currency_id = fields.Many2one("res.currency")

    card_required = fields.Boolean(
        compute="_compute_card_required",
        store=False,
    )

    @api.depends("journal_id")
    def _compute_card_required(self):
        for record in self:
            record.card_required = (
                record.journal_id.is_card_journal if record.journal_id else False
            )

    @api.constrains("card_id", "journal_id")
    def _check_card_required(self):
        for record in self:
            if record.card_required and not record.card_id:
                raise ValidationError(
                    _("Card Used is required for this type of journal")
                )
