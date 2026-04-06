from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    user_can_view_amount_on_groupby = fields.Boolean(
        compute="_compute_user_can_view_amount_on_groupby",
        help="Check if current user can view amount fields when groupby is applied",
    )

    @api.depends_context("group_by")
    def _compute_user_can_view_amount_on_groupby(self):
        group = self.env.ref(
            "counter_sale.group_counter_sale_hide_amount_on_groupby",
            raise_if_not_found=False,
        )
        user_in_group = group and self.env.user in group.users
        group_by = self.env.context.get("group_by")

        for rec in self:
            rec.user_can_view_amount_on_groupby = (
                (not user_in_group) if group_by else True
            )

    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """Override read_group to restrict field access on grouped searches"""
        group = self.env.ref(
            "counter_sale.group_counter_sale_hide_amount_on_groupby",
            raise_if_not_found=False,
        )
        user_in_group = group and self.env.user in group.users

        if user_in_group and groupby:
            fields = [
                f
                for f in fields
                if f
                not in [
                    "amount_total_signed",
                    "amount_untaxed_signed",
                    "amount_tax_signed",
                    "amount_total_in_currency_signed",
                    "amount_residual_signed",
                    "amount_residual",
                    "user_can_view_amount_on_groupby",
                ]
            ]

        result = super().read_group(
            domain=domain,
            fields=fields,
            groupby=groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

        return result

    def _get_additional_info(self, document):
        res = super(AccountMove, self)._get_additional_info(document)
        res.extend(
            [
                {"nombre": "Vendedor", "valor": str(self.user_id.name)},
                {"nombre": "Correo", "valor": str(self.company_id.email)},
                {
                    "nombre": "Contribuyente",
                    "valor": "Agente de Retención - Resolución Nro. NAC-DNCRASC20-00000001",
                },
            ]
        )
        return res
