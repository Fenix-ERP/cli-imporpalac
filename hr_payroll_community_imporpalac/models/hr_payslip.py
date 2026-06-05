from odoo import api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def get_filtered_lines(self, payslip_id):
        payslip = self.env["hr.payslip"].browse(payslip_id)
        filtered_lines = payslip.line_ids.filtered(
            lambda line: line.appears_on_payslip and line.total != 0
        )

        allowances = filtered_lines.filtered(
            lambda line: line.category_id.code in ["BASIC", "ALW"]
        )
        deductions = filtered_lines.filtered(
            lambda line: line.category_id.code == "DED"
            and "fondos de reserva acumulados" not in (line.name or "").lower()
        )

        num_lines = range(max(len(allowances), len(deductions)))
        html_lines = ""

        for n in num_lines:
            allowance_line = allowances[n] if n < len(allowances) else False
            deduction_line = deductions[n] if n < len(deductions) else False

            html_lines += """
                <tr>
                    <td style="border-left: 1px solid black; width: 175px;">
                        <t t-if="allowance_line">
                            <span style="margin-left: 10px;">{}</span>
                        </t>
                    </td>
                    <td style="width: 100px; text-align: right;">
                        <t t-if="allowance_line">
                            <span style="margin-right: 10px;">{}</span>
                        </t>
                    </td>
                    <td style="border-left: 1px solid black; width: 175px;">
                        <t t-if="deduction_line">
                            <span style="margin-left: 10px;">{}</span>
                        </t>
                    </td>
                    <td style="border-right: 1px solid black; width: 75px; text-align: right;">
                        <t t-if="deduction_line">
                            <span style="margin-right: 10px;">{}</span>
                        </t>
                    </td>
                </tr>
            """.format(
                allowance_line.name if allowance_line else "",
                "{:,.2f}".format(allowance_line.total) if allowance_line else "",
                deduction_line.name if deduction_line else "",
                "{:,.2f}".format(deduction_line.total) if deduction_line else "",
            )

        return html_lines
