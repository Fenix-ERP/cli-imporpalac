from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"
    is_rectified = fields.Boolean(default=False, readonly=True)

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

    def _create_pdc_payment(self, invoice, payment_line):
        payment_type = (
            "money_send" if invoice.move_type == "in_invoice" else "money_receive"
        )
        cashier_env = self.env(user=payment_line.payment_id.user_id)
        cashier_env.su = True
        ctx = cashier_env.context
        wizard_vals = {
            "partner_name": ctx.get("default_partner_name", invoice.partner_id.id),
            "payment_amount": payment_line.amount,
            "invoice_ids": [(6, 0, ctx.get("default_invoice_ids", [invoice.id]))],
            "agent": payment_line.chq_agent,
            "payment_date": payment_line.chq_payment_date,
            "bank_details": payment_line.chq_bank_details.id,
            "due_date": payment_line.chq_due_date,
            "chq_refr": payment_line.chq_refr,
            "payment_type": payment_type,
            "journal_payment": payment_line.journal_id.id,
            "is_boolean": (
                True
                if invoice.env.company.pdc_settlement_order == "autopaid"
                else False
            ),
        }
        pdc_wizard = cashier_env["post.cheque.wizard"].create(wizard_vals)
        result = pdc_wizard.button_register()
        post_cheque = cashier_env["post.cheque"].browse(result.get("res_id"))
        post_cheque.write({"invoice_ids": [(6, 0, [invoice.id])]})
        post_cheque.with_context(last_deposit=False).deposting_action()
        pdc_move = cashier_env["account.move"].search(
            [
                "|",
                ("pd_cheque_id", "=", post_cheque.id),
                ("pd_reconciliation_id", "in", [post_cheque.id]),
            ]
        )

        return pdc_move

    def _create_payment(self, partner_id, payment_line):
        cashier_env = self.env(user=payment_line.payment_id.user_id)
        payment_obj = cashier_env["account.payment"]
        payment = payment_obj.sudo().create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner_id.id,
                "amount": payment_line.amount,
                "payment_method_line_id": payment_line.payment_method_line_id.id,
                "journal_id": payment_line.journal_id.id,
                "payment_card_id": payment_line.card_id.id,
                "global_reference": payment_line.reference,
                "voucher_reference": (
                    payment_line.reference if payment_line.card_id.id else False
                ),
                "date": fields.Date.today(),
                "company_id": payment_line.payment_id.company_id.id,
                # "currency_id": journal_id.currency_id,
            }
        )
        payment.action_post()
        return payment

    def button_validate(self):
        self = self.sudo()
        res = super(StockPicking, self).button_validate()
        if res:
            for picking in self:
                if picking.state != "done" and picking.picking_type_code == "outgoing":
                    raise ValidationError(_("The delivery has not been completed."))
                sale_order = picking.sudo().sale_id
                picking.user_id = self.env.user
                if sale_order and not picking.return_id:
                    if self.payment_state == "not_paid":
                        raise ValidationError(
                            _(
                                "This picking has not yet been paid, "
                                "please request payment at the checkout."
                            )
                        )

                    invoice = sale_order._create_invoices()
                    invoice.write({"payment_method": picking.payment_method.id})
                    if sale_order.note:
                        sale_order.invoice_ids.write({"narration": sale_order.note})
                    if sale_order.lines_info_additional:
                        sale_order.invoice_ids.write(
                            {
                                "lines_info_additional": [
                                    (
                                        0,
                                        0,
                                        {
                                            "name": info.name,
                                            "description": info.description,
                                        },
                                    )
                                    for info in sale_order.lines_info_additional
                                ]
                            }
                        )
                    invoice.action_post()
                    sale_payment = sale_order.payment_ids
                    first_payment = sale_payment[0] if sale_payment else False
                    if first_payment:
                        for payment_line in first_payment.payment_line_ids:
                            if payment_line.chq_refr:
                                self.with_context(
                                    check_global_reference=True
                                )._create_pdc_payment(invoice, payment_line)
                            else:
                                payment = self.with_context(
                                    check_global_reference=True
                                )._create_payment(invoice.partner_id, payment_line)
                                invoice_receivable_accounts = invoice.line_ids.filtered(
                                    lambda line: line.account_id.account_type
                                    == "asset_receivable"
                                ).mapped("account_id")
                                for line in payment.move_id.line_ids:
                                    if (
                                        line.account_id in invoice_receivable_accounts
                                        and line.balance < 0
                                    ):
                                        invoice.js_assign_outstanding_line(line.id)
                                        break

                    invoice.with_delay().send_electronic_document()
                    invoice.info_message = "En cola de autorización"
                    invoice.state_send_document = "in_process"
                    picking.invoice_number = invoice.name
        return res

    def write(self, vals):
        res = super().write(vals)
        has_moves = "move_ids" in vals or "move_ids_without_package" in vals
        if not has_moves:
            return res
        if not self.picker_user_id:
            self.move_ids.sudo().write({"state": "waiting"})
        elif self.picker_user_id and not self.user_id:
            self.move_ids.sudo().write({"state": "confirmed"})
        return res

    def _check_assignable(self):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        has_issue = 0
        for move in self.move_ids:
            precision = move.product_uom.rounding or 0.0001
            product_name = move.product_id.display_name or _("Unknown Product")
            demand = move.product_uom_qty
            quant = move.quantity
            has_issue = has_issue + 1 if move.has_issue else has_issue
            if float_compare(demand, quant, precision_rounding=precision) > 0:
                if not move.has_issue:
                    raise ValidationError(
                        _(
                            "Quantity of product '%s' must be equals to demand. "
                            "Please assign a issue to report this picking.",
                            product_name,
                        )
                    )
        if has_issue > 0:
            if self.issue_reported:
                return False
            target = self.sale_id or self.purchase_id
            if not target:
                return False
            user_id = target.user_id
            summary = _("Issue detected in Picking %s", (self.name or ""))
            note = _(
                "<h5>Order Issue Report</h5>"
                "<br/>Please review this order due to the following issues:"
            )
            for move in self.move_ids:
                if move.has_issue:
                    selection = move._fields["issue_type"]._description_selection(
                        self.env
                    )
                    issue_label = next(
                        (lbl for val, lbl in selection if val == move.issue_type),
                        move.issue_type,
                    )
                    note += _(
                        "<ul>"
                        "<p><b>%(product)s</b></p>"
                        "<li>Problem: %(issue_type)s</li>"
                        "<li>Quants: %(issue_qty)s/%(demand_qty)s</li>"
                        "<li>Observations: %(issue_notes)s</li>"
                        "</ul>"
                    ) % {
                        "product": move.product_id.display_name,
                        "issue_type": issue_label,
                        "issue_qty": move.issue_qty,
                        "demand_qty": move.product_uom_qty,
                        "issue_notes": move.issue_notes or "-",
                    }
            activity_vals = {
                "res_model_id": self.env["ir.model"]._get_id(target._name),
                "res_id": target.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": user_id.id,
                "summary": summary,
                "note": note,
            }
            Channel = self.env["discuss.channel"]
            channel_id = Channel.channel_get([user_id.partner_id.id])
            channel_id.message_post(
                body=_("There are issues with your order: ") + target._get_html_link(),
                author_id=self.env.user.partner_id.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            self.sudo().write({"issue_reported": True})
            self.env["mail.activity"].create(activity_vals)
        return not has_issue

    @api.model
    def action_confirm_by_picker(self, data):
        confirm_res = super(StockPicking, self).action_confirm_by_picker(data)
        if confirm_res:
            picking = self.browse(confirm_res.get("picking_id", False))
            if picking.exists():
                res = picking._check_assignable()
                if not res and picking.picking_type_code == "outgoing":
                    picking.move_ids.sudo().write({"state": "confirmed"})
                    return {
                        "picking_id": picking.id,
                        "picking_name": picking.name,
                        "picking_state": picking.state,
                        "message": _("This picking has been reported correctly."),
                        "user_id": picking.picker_user_id.name,
                    }
        return confirm_res

    def action_confirm_picking(self):

        for picking in self:
            res = picking._check_assignable()
            if not res and picking.picking_type_code == "outgoing":
                return self.env.user.notify_warning(
                    message=_("This picking has been reported correctly."),
                    title=_("Issue Reported"),
                )
        return super(StockPicking, self).action_confirm_picking()


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    def action_assign(self):
        """Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.mapped("package_level_ids").filtered(
            lambda pl: pl.state == "draft" and not pl.move_ids
        )._generate_moves()
        self.filtered(lambda picking: picking.state == "draft").action_confirm()
        moves = self.move_ids.filtered(
            lambda move: move.state not in ("draft", "cancel", "done")
        ).sorted(
            key=lambda move: (
                -int(move.priority),
                not bool(move.date_deadline),
                move.date_deadline,
                move.date,
                move.id,
            )
        )
        moves._action_assign()
        return True
