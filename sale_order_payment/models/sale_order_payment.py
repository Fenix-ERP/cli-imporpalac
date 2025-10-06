from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderPayment(models.Model):
    _name = "sale.order.payment"
    _description = "Sale Order Payment"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        default=lambda self: self.env["ir.sequence"].next_by_code("sale.order.payment"),
    )

    client_id = fields.Many2one(
        related="order_id.partner_id", string="Client", store=True
    )
    user_id = fields.Many2one("res.users", string="Cashier")
    order_id = fields.Many2one("sale.order", string="Sale Order")
    rectified_order_id = fields.Many2one("sale.order", string="Rectified Sale Order")

    date_order = fields.Date(string="Order Date")
    rectified_date_order = fields.Date(string="Rectified Order Date")

    hour_register = fields.Datetime(string="Payment Register Time")

    amount = fields.Monetary(
        compute="_compute_amount", currency_field="currency_id", store=True
    )
    rectified_amount = fields.Monetary()

    difference = fields.Monetary(compute="_compute_difference", store=True)

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
        "account.payment.method.line",
        compute="_compute_payment_method_line_fields",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    is_mixed_payment = fields.Boolean(
        string="Mix payment", default=False, readonly=False
    )
    card_id = fields.Many2one("account.card", string="Card Used")
    reference = fields.Char()
    state = fields.Selection(
        [
            ("draft", "Pending"),
            ("processed", "Processed"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )
    is_pdc = fields.Boolean(default=False)

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
        default=False,
    )
    payment_line_ids = fields.One2many(
        "sale.order.payment.line",
        "payment_id",
        string="Payment lines",
        copy=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )

    delivery_status = fields.Selection(
        related="order_id.delivery_status",
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
        self = self.with_context(check_global_reference=True)
        for payment in self:
            if (
                payment.delivery_status != "to_deliver"
                and payment.payment_method.code != "cash"
            ):
                raise UserError(
                    _(
                        "This payment cannot be processed because "
                        "the order has not been delivered."
                    )
                )

            skip_open = self.env.context.get("skip_open_payment_method_wizard", False)
            if not skip_open:
                method_lines = payment.journal_id.inbound_payment_method_line_ids
                if method_lines:
                    domain = self.available_payment_method_line_ids.ids
                    ctx = {
                        "default_sale_order_payment_id": self.id,
                        "default_balance": self.amount,
                        "default_payment_method_domain": f"[('id', 'in', {domain})]" "",
                        "default_chq_agent": self.client_id.name,
                    }
                    ctx.update({"payment_method": self.payment_method.code})
                    if (
                        len(method_lines) > 1
                        or self.payment_method.code
                        in ["credit_card", "postdated_check"]
                        or self.is_mixed_payment
                    ):

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
                            "context": ctx,
                        }
            if not self.is_mixed_payment and not self.is_pdc:
                self.env["sale.order.payment.line"].create(
                    {
                        "payment_id": self.id,
                        "journal_id": self.journal_id.id,
                        "payment_method_line_id": self.payment_method_line_id.id,
                        "amount": self.amount,
                        "card_id": self.card_id.id,
                        "reference": self.reference,
                    }
                )
            payment.state = "processed"
            payment.hour_register = datetime.now()
            payment.order_id.picking_ids.sudo().write({"payment_state": "paid"})
            payment.user_id = self.env.user.id

    def unlink(self):
        if not self._context.get("force_delete"):
            raise UserError(_("Payments cannot be deleted."))
        return super().unlink()


class SaleOrderPaymentLine(models.Model):
    _name = "sale.order.payment.line"
    _description = "Sale Order Payment Line"
    payment_id = fields.Many2one(
        comodel_name="sale.order.payment",
        required=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
        copy=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        readonly=False,
        copy=False,
        domain="payment_method_domain",
    )
    client_id = fields.Many2one(
        related="payment_id.client_id", string="Customer", readonly=True
    )
    payment_state = fields.Selection(
        related="payment_id.state", string="Payment State", readonly=True
    )
    reference = fields.Char()
    chq_agent = fields.Char(string="Agent")
    chq_refr = fields.Char(string="PDC N° Check")
    chq_bank_details = fields.Many2one("res.bank", string="PDC Bank Info")
    chq_payment_date = fields.Date(string="PDC Payment Date")
    chq_due_date = fields.Date(string="PDC Due Date")
    card_id = fields.Many2one("account.card", string="Card Used")
    amount = fields.Monetary(required=True, default=0)
    currency_id = fields.Many2one("res.currency", string="Currency")

    @api.constrains("reference", "payment_method_line_id", "journal_id")
    def _check_global_reference(self):
        if not self.env.context.get("check_global_reference"):
            return
        lines = self.payment_id.payment_line_ids
        duplicates = lines.filtered(
            lambda line: len(
                lines.filtered(
                    lambda x: x.reference == line.reference
                    and x.payment_method_line_id == line.payment_method_line_id
                    and x.card_id == line.card_id
                )
            )
            > 1
        )
        if duplicates:
            raise ValidationError(_("There are duplicated references"))
        duplicates = []
        bank_journals = self.env["account.journal"].search([("type", "=", "bank")])
        incoming_accounts = bank_journals.mapped(
            "inbound_payment_method_line_ids.payment_account_id"
        )
        outgoing_accounts = bank_journals.mapped(
            "outbound_payment_method_line_ids.payment_account_id"
        )
        bank_accounts = incoming_accounts + outgoing_accounts
        bank_lines = self.filtered(
            lambda line: line.payment_method_line_id.payment_account_id in bank_accounts
        )
        if not bank_lines:
            return
        lines_with_ref = bank_lines.filtered(lambda line: line.reference)
        if not lines_with_ref:
            raise UserError(_("Please enter a Reference to continue."))
        account_id = bank_lines.payment_method_line_id.payment_account_id
        query = """
            SELECT ap.id,ap.global_reference
            FROM account_payment ap
            INNER JOIN account_payment_method_line apml
                ON apml.id = ap.payment_method_line_id
            INNER JOIN account_move am
                ON am.id = ap.move_id
            WHERE apml.payment_account_id IN %s
              AND ap.global_reference = %s
              AND am.state = 'posted'
              {filter_card_payment}
            GROUP BY ap.id, ap.global_reference
            HAVING COUNT(*) >= 1
        """.format(
            filter_card_payment=("AND ap.payment_card_id = %s" if self.card_id else "")
        )
        params = [tuple(account_id.ids), self.reference]
        if self.card_id:
            params.append(self.card_id.id)

        self.env.cr.execute(query, params)
        duplicates.extend(self.env.cr.fetchall())

        query = """
            SELECT sopl.id,sopl.reference
            FROM sale_order_payment_line sopl
            INNER JOIN account_payment_method_line apml
                ON apml.id = sopl.payment_method_line_id
            INNER JOIN sale_order_payment sop
                ON sop.id = sopl.payment_id
            WHERE apml.payment_account_id IN %s
              AND sopl.id != %s
              AND sopl.reference = %s
              AND sop.state = 'processed'
              {filter_card_sale}
            GROUP BY sopl.id, sopl.reference
            HAVING COUNT(*) >= 1
        """.format(
            filter_card_sale="AND sopl.card_id = %s" if self.card_id else ""
        )
        params = [tuple(account_id.ids), self.id, self.reference]
        if self.card_id:
            params.append(self.card_id.id)

        self.env.cr.execute(query, params)
        duplicates.extend(self.env.cr.fetchall())

        if duplicates:
            dup_refs = duplicates[0][1]
            acc_names = ", ".join([acc.name for acc in account_id])
            error = _(
                "The following Reference(s): '%(dup_refs)s' are duplicated"
                " for the bank accounts: '%(account)s'"
            ) % {
                "dup_refs": dup_refs,
                "account": acc_names,
            }
            if self.card_id:
                error += _(
                    " with the card: '%(card)s'.",
                    card=self.card_id.name,
                )
            raise ValidationError(error)


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
