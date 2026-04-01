from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.constrains("payment_method_line_id", "global_reference", "journal_id")
    def _check_unique_global_reference(self):
        self.ensure_one()
        context_params = self.env.context.get("params") or {}
        if context_params.get("model") == "account.card.settlement":
            return
        if self.env.context.get("skip_check_global_reference"):
            return
        if self.journal_id.type != "bank":
            return
        if not self.global_reference:
            return
        account_id = self.payment_method_line_id.payment_account_id
        duplicates = []
        query = """
            SELECT ap.id,ap.global_reference
            FROM account_payment ap
            INNER JOIN account_payment_method_line apml
                ON apml.id = ap.payment_method_line_id
            INNER JOIN account_move am
                ON am.id = ap.move_id
            WHERE apml.payment_account_id IN %s
              AND ap.id != %s
              AND ap.global_reference = %s
              AND am.state = 'posted'
              {filter_card_payment}
            GROUP BY ap.id, ap.global_reference
            HAVING COUNT(*) >= 1
        """.format(
            filter_card_payment=(
                "AND ap.payment_card_id = %s" if self.payment_card_id else ""
            )
        )
        params = [tuple(account_id.ids), self.id, self.global_reference]
        if self.payment_card_id:
            params.append(self.payment_card_id.id)

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
              AND sopl.reference = %s
              AND sop.state = 'processed'
              {filter_card_sale}
            GROUP BY sopl.id, sopl.reference
            HAVING COUNT(*) >= 1
        """.format(
            filter_card_sale="AND sopl.card_id != %s" if self.payment_card_id else ""
        )
        params = [tuple(account_id.ids), self.global_reference]
        if self.payment_card_id:
            params.append(self.payment_card_id.id)

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
            if self.payment_card_id:
                error += _(
                    " with the card: '%(card)s'.",
                    card=self.payment_card_id.name,
                )
            raise ValidationError(error)
