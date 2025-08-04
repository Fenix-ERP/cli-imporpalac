from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

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
