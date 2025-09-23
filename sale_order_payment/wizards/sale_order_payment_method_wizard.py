from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round


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
    partner_id = fields.Many2one(
        related="sale_order_payment_id.client_id", string="Customer", readonly=True
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
    chq_agent = fields.Char(string="Agent")
    chq_refr = fields.Char(string="N° Check")
    chq_bank_details = fields.Many2one("res.bank", string="Bank Info")
    chq_payment_date = fields.Date(
        string="Payment Date", default=fields.Date.context_today
    )
    chq_due_date = fields.Date(string="Due Date", default=fields.Date.context_today)
    chq_amount = fields.Monetary(string="PDC Amount")
    is_pdc = fields.Boolean(store=False, compute="_compute_is_pdc")
    balance = fields.Monetary(readonly=True)
    residual = fields.Monetary(readonly=True, compute="_compute_residual_amount")
    method_line_ids = fields.One2many(
        "sale.order.payment.method.line.wizard",
        "wizard_id",
        string="Method lines",
        copy=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    available_journal_ids = fields.Many2many(
        "account.journal", compute="_compute_available_journals"
    )

    @api.depends("balance")
    def _compute_is_pdc(self):
        for record in self:
            record.is_pdc = record.sale_order_payment_method_code == "postdated_check"

    @api.depends("sale_order_payment_method_code")
    def _compute_available_journals(self):
        if self.sale_order_payment_method_code == "credit_card":
            domain = [("type", "in", ["bank", "cash"])]
        else:
            domain = [("type", "in", ["bank", "cash"]), ("is_card_journal", "=", False)]
        self.available_journal_ids = self.env["account.journal"].search(domain)

    @api.depends("method_line_ids", "balance", "chq_amount")
    def _compute_residual_amount(self):
        for wizard in self:
            total_payed = sum(line.amount for line in wizard.method_line_ids)
            self.residual = self.balance - self.chq_amount - total_payed

    @api.constrains("method_line_ids", "balance", "chq_amount")
    def _check_total_amount(self):
        for wizard in self:
            if not wizard.is_mixed_payment:
                continue
            total = sum(line.amount for line in wizard.method_line_ids)
            total += wizard.chq_amount

            total = float_round(total, precision_digits=2)
            balance = float_round(wizard.balance, precision_digits=2)

            if total < balance:
                raise ValidationError(
                    _(
                        "The total amount of payment lines (%(total).2f) must be equal"
                        " to or greater than the total balance (%(amount).2f).",
                        total=total,
                        amount=balance,
                    )
                )

    def _check_unique_cheque_per_client(self):
        for record in self:
            duplicates = (
                self.env["post.cheque"]
                .sudo()
                .search(
                    [
                        ("chq_refr", "=", record.chq_refr),
                        ("partner_name", "=", record.partner_id.id),
                        ("state", "!=", "cancel"),
                    ],
                    limit=1,
                )
            )
            self_duplicates = (
                self.env["sale.order.payment.line"]
                .sudo()
                .search(
                    [
                        ("chq_refr", "=", record.chq_refr),
                        ("client_id", "=", record.partner_id.id),
                        ("payment_state", "!=", "cancel"),
                    ],
                    limit=1,
                )
            )

            if duplicates or self_duplicates:
                raise ValidationError(
                    _("This check number already exists for this customer.")
                )

    def action_confirm(self):
        self.ensure_one()
        self.sale_order_payment_id.reference = self.reference
        self.sale_order_payment_id.card_id = self.card_id
        for line in self.method_line_ids:
            self.env["sale.order.payment.line"].create(
                {
                    "payment_id": self.sale_order_payment_id.id,
                    "journal_id": line.journal_id.id,
                    "payment_method_line_id": line.payment_method_line_id.id,
                    "amount": line.amount,
                    "card_id": line.card_id.id,
                    "reference": line.reference,
                }
            )
        if self.is_pdc:
            self._check_unique_cheque_per_client()
            self.sale_order_payment_id.is_pdc = True
            self.env["sale.order.payment.line"].create(
                {
                    "payment_id": self.sale_order_payment_id.id,
                    "journal_id": self.sale_order_payment_id.journal_id.id,
                    "amount": (
                        self.chq_amount if self.is_mixed_payment else self.balance
                    ),
                    "chq_agent": self.chq_agent,
                    "chq_refr": self.chq_refr,
                    "chq_bank_details": self.chq_bank_details.id,
                    "chq_payment_date": self.chq_payment_date,
                    "chq_due_date": self.chq_due_date,
                }
            )

        return self.with_context(
            skip_open_payment_method_wizard=True
        ).sale_order_payment_id.process_payment()


class SaleOrderPaymentMethodLine(models.TransientModel):
    _name = "sale.order.payment.method.line.wizard"
    _description = "Sale Order Payment Method Line Wizard"
    wizard_id = fields.Many2one(
        comodel_name="sale.order.payment.method.wizard",
        required=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
        copy=True,
    )
    sale_order_payment_method_code = fields.Char(
        string="Payment method",
        related="wizard_id.sale_order_payment_method_code",
        readonly=True,
    )
    available_journal_ids = fields.Many2many(
        "account.journal",
        related="wizard_id.available_journal_ids",
        readonly=True,
    )
    reference = fields.Char()
    journal_id = fields.Many2one("account.journal", string="Journal", required=True)
    available_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line", compute="_compute_payment_method_line_fields"
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
    card_required = fields.Boolean(
        compute="_compute_card_required",
        store=False,
    )

    amount = fields.Monetary(required=True, default=0)
    currency_id = fields.Many2one("res.currency")

    @api.depends("journal_id")
    def _compute_payment_method_line_fields(self):
        for rec in self:
            rec.available_payment_method_line_ids = (
                rec.journal_id._get_available_payment_method_lines("inbound")
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
