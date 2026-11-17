from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"
    is_rectified = fields.Boolean(default=False, readonly=True)
    is_inter_company = fields.Boolean(compute="_compute_is_inter_company", store=False)

    @api.depends("partner_id")
    def _compute_is_inter_company(self):
        internal_partners = (
            self.env["res.company"].sudo().search([]).mapped("partner_id")
        )
        for picking in self:
            picking.is_inter_company = picking.partner_id in internal_partners

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
        payment_method_line = payment_line.payment_method_line_id
        if (
            not payment_method_line
            or payment_method_line.journal_id != payment_line.journal_id
        ):
            payment_method_line = (
                payment_line.journal_id._get_available_payment_method_lines("inbound")[
                    :1
                ]._origin
            )
        if not payment_method_line:
            raise ValidationError(
                _(
                    "There is no payment method available for journal %s.",
                    payment_line.journal_id.display_name,
                )
            )
        payment = payment_obj.sudo().create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner_id.id,
                "amount": payment_line.amount,
                "payment_method_line_id": payment_method_line.id,
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

    def _get_picking_invoice(self, sale_order, invoices_by_order):
        invoice = invoices_by_order.get(sale_order.id)
        if invoice is not None:
            return invoice
        invoice = sale_order.with_context(
            raise_if_nothing_to_invoice=False
        )._create_invoices()
        if not invoice:
            invoice = sale_order.invoice_ids.filtered(
                lambda move: move.state == "draft"
            ).sorted("id")[-1:]
        if not invoice:
            invoice = sale_order.invoice_ids.filtered(
                lambda move: move.state == "posted"
            ).sorted("id")[-1:]
        invoices_by_order[sale_order.id] = invoice
        return invoice

    def _prepare_draft_invoices(self, invoice, picking, sale_order):
        draft_invoices = invoice.filtered(lambda move: move.state == "draft")
        if not draft_invoices:
            return draft_invoices
        draft_invoices.sudo().write(
            {
                "payment_method": picking.payment_method.id,
                "pf_branch_id": sale_order.pf_branch_id.id,
            }
        )
        if sale_order.note:
            draft_invoices.write({"narration": sale_order.note})
        if sale_order.lines_info_additional:
            draft_invoices.write(
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
        draft_invoices.action_post()
        return draft_invoices

    def _register_invoice_payment(self, invoice, payment_line):
        skip_ctx = self.with_context(skip_check_global_reference=True)
        if payment_line.chq_refr:
            skip_ctx._create_pdc_payment(invoice, payment_line)
            return
        payment = skip_ctx._create_payment(invoice.partner_id, payment_line)
        payment.sudo().write({"ref": invoice.name})
        invoice_receivable_accounts = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        ).mapped("account_id")
        for line in payment.move_id.line_ids:
            if line.account_id in invoice_receivable_accounts and line.balance < 0:
                invoice.js_assign_outstanding_line(line.id)
                break

    def _process_invoice_payments(self, invoice, sale_order):
        sale_payment = sale_order.payment_ids
        first_payment = sale_payment[0] if sale_payment else False
        if not first_payment or invoice.currency_id.is_zero(invoice.amount_residual):
            return
        for payment_line in first_payment.payment_line_ids:
            self._register_invoice_payment(invoice, payment_line)

    def _queue_invoice_electronic_document(self, draft_invoices):
        if not draft_invoices:
            return
        draft_invoices.with_delay().action_send_electronic_document()
        draft_invoices.info_message = "En cola de autorización"
        draft_invoices.state_send_document = "in_process"

    def _process_picking_invoice(self, picking, invoices_by_order):
        if picking.state != "done" and picking.picking_type_code == "outgoing":
            raise ValidationError(_("The delivery has not been completed."))
        sale_order = picking.sudo().sale_id
        picking.user_id = self.env.user
        if picking.is_inter_company or not sale_order or picking.return_id:
            return
        if picking.payment_state == "not_paid":
            raise ValidationError(
                _(
                    "This picking has not yet been paid, "
                    "please request payment at the checkout."
                )
            )
        invoice = self._get_picking_invoice(sale_order, invoices_by_order)
        if not invoice:
            return
        draft_invoices = self._prepare_draft_invoices(invoice, picking, sale_order)
        self._process_invoice_payments(invoice, sale_order)
        self._queue_invoice_electronic_document(draft_invoices)
        picking.invoice_number = invoice.name

    def button_validate(self):
        self = self.sudo()
        res = super(StockPicking, self).button_validate()
        if not res:
            return res
        invoices_by_order = {}
        for picking in self:
            self._process_picking_invoice(picking, invoices_by_order)
        return res

    def _check_confirmable(self):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        has_issue = 0
        if self.picking_type_code not in ("outgoing", "incoming"):
            return True
        for move in self.move_ids:
            precision = move.product_uom.rounding or 0.0001
            product_name = move.product_id.display_name or _("Unknown Product")
            demand = move.product_uom_qty
            quant = move.quantity

            has_issue = has_issue + 1 if move.has_issue else has_issue
            if quant < 0:
                raise ValidationError(
                    _("Quantity of product %s must be not negative") % product_name
                )
            if move.issue_qty < 0:
                raise ValidationError(
                    _("Quantity of product %s in Issue must be not negative")
                    % product_name
                )
            if (
                not self.picking_type_code == "incoming"
                and float_compare(demand, quant, precision_rounding=precision) > 0
            ):
                if not move.has_issue:
                    raise ValidationError(
                        _(
                            "Quantity of product '%s' must be equals to demand. "
                            "Please assign a issue to report this picking.",
                            product_name,
                        )
                    )
        if has_issue > 0:
            if self.collection_state == "issue":
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
            self.collection_state = "issue"
            self.sudo().env["mail.activity"].create(activity_vals)
        return not has_issue

    @api.model
    def action_confirm_by_picker(self, data):
        confirm_res = super(StockPicking, self).action_confirm_by_picker(data)
        if confirm_res:
            picking = self.browse(confirm_res.get("picking_id", False))
            if picking.exists():
                res = picking._check_confirmable()
                if not res and picking.picking_type_code == "outgoing":
                    picking.collection_state = "issue"
                    return {
                        "picking_id": picking.id,
                        "picking_name": picking.name,
                        "picking_state": picking.state,
                        "collection_state": picking.collection_state,
                        "message": _("This picking has been reported correctly."),
                        "user_id": picking.picker_user_id.name,
                    }
        return confirm_res

    def action_confirm_picking(self):
        res = super(StockPicking, self).action_confirm_picking()
        for picking in self:
            confirmable = picking._check_confirmable()
            if not confirmable and picking.picking_type_code == "outgoing":
                return self.env.user.notify_warning(
                    message=_("This picking has been reported correctly."),
                    title=_("Issue Reported"),
                )
        return res


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
