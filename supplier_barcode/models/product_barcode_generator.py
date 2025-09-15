# Copyright (C) Softhealer Technologies.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

try:
    import barcode

    _lib_imported = True
except ImportError:
    _lib_imported = False
import base64
import random

import werkzeug.exceptions


def get_random_number():
    random_num = str(random.randint(10000000000, 99999999999))
    random_first_digit = random.randint(1, 9)
    random_str = str(random_first_digit) + "".join(map(str, random_num[:11]))
    return random_str


def generate_ean(barcode_type):
    if not _lib_imported:
        raise UserError(_("python-barcode is not installed. Please install it."))
    EAN = barcode.get_barcode_class(barcode_type)
    ean = EAN(get_random_number())
    return ean.get_fullcode()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    barcode_supp = fields.Char("Supplier Barcode", compute="_compute_supp_barcode")

    @api.depends("product_variant_ids.barcode_supp")
    def _compute_supp_barcode(self):
        self._compute_template_field_from_variant_field("barcode_supp")

    sh_product_barcode_img_supp = fields.Binary(
        string="Supplier Barcode Image", readonly=True
    )

    @api.model
    def get_barcodes(self, product_id):
        barcodes = super(ProductTemplate, self).get_barcodes(product_id)
        product_id = self.browse(product_id)
        if not product_id.exists():
            raise ValidationError(_("Product template not found."))
        if product_id.barcode_supp:
            barcodes.append(product_id.barcode_supp)
        return barcodes

    def action_generate_barcode_image_supp(self):
        self.ensure_one()
        if self.barcode_supp:
            img_barcode = self.env["ir.actions.report"].barcode(
                "Code128", self.barcode_supp, width=500, height=90, humanreadable=0
            )
            self.sh_product_barcode_img_supp = base64.b64encode(img_barcode)

    def generate_barcode_image_supp(self, ean):
        # generate Barcode image
        try:
            ean_barcode = self.env["ir.actions.report"].barcode(
                "EAN13", ean, width=500, height=90, humanreadable=0
            )
            if ean_barcode:
                self.sh_product_barcode_img_supp = base64.b64encode(ean_barcode)

        except (ValueError, AttributeError) as err:
            raise werkzeug.exceptions.HTTPException(
                description="Cannot convert into barcode."
            ) from err

    def action_generate_barcode_supp(self):
        if self:
            for rec in self:
                ean = generate_ean(self.env.company.sh_barcode_type)
                rec.barcode_supp = ean
                rec.generate_barcode_image_supp(ean)


class ShProductProduct(models.Model):
    _inherit = "product.product"
    barcode_supp = fields.Char(
        "Supplier Barcode",
        copy=False,
        index="btree_not_null",
        help="International Supplier Article Number used for product identification.",
    )

    def action_generate_barcode_image_supp(self):
        self.ensure_one()
        if self.barcode_supp:
            img_barcode = self.env["ir.actions.report"].barcode(
                "Code128", self.barcode_supp, width=500, height=90, humanreadable=0
            )
            self.sh_product_barcode_img_supp = base64.b64encode(img_barcode)

    def action_generate_barcode_supp(self):
        if self:
            for rec in self:
                ean = generate_ean(self.env.company.sh_barcode_type)
                rec.barcode_supp = ean
                rec.generate_barcode_image_supp(ean)

    def generate_barcode_image_supp(self, ean):
        # generate Barcode image
        try:
            ean_barcode = self.env["ir.actions.report"].barcode(
                "EAN13", ean, width=500, height=90, humanreadable=0
            )
            if ean_barcode:
                self.sh_product_barcode_img_supp = base64.b64encode(ean_barcode)

        except (ValueError, AttributeError) as err:
            raise werkzeug.exceptions.HTTPException(
                description="Cannot convert into barcode."
            ) from err

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ShProductProduct, self).create(vals_list)
        if (
            self.user_has_groups("sh_barcode_generator_simple.group_barcode_generator")
            and self.env.company.generate_barcode_on_product
        ):
            # Filter out no barcode products
            barcode_not_generated_product = res.filtered(
                lambda product: not product.barcode_supp
            )
            for product in barcode_not_generated_product:
                # generate product barcode
                ean = generate_ean(self.env.company.sh_barcode_type)
                product.barcode_supp = ean
                product.generate_barcode_image_supp(ean)

        return res


class GenerateProductBarcode(models.Model):
    _name = "generate.product.barcode.supp"
    _description = "Generate Product Barcode"

    # Generate Barcode for Existing Product
    overwrite_existing = fields.Boolean("Overwrite Barcode If Exists")

    def generate_barcode(self):
        if self.user_has_groups("sh_barcode_generator_simple.group_barcode_generator"):

            context = dict(self._context or {})
            active_ids = context.get("active_ids", []) or []
            active_model = context.get("active_model", []) or []

            if active_model == "product.product":
                for record in self.env["product.product"].browse(active_ids):

                    new_barcode = ""
                    if record.id:
                        new_barcode = generate_ean(self.env.company.sh_barcode_type)
                        if self.overwrite_existing:  # Overwrite existing
                            record.barcode_supp = new_barcode
                            record.generate_barcode_image_supp(new_barcode)
                        else:
                            if (
                                not record.barcode_supp
                            ):  # If barcode exists,then don't overwrite, Else generate New
                                record.barcode_supp = new_barcode
                                record.generate_barcode_image_supp(new_barcode)

            elif active_model == "product.template":
                for record in self.env["product.template"].browse(active_ids):
                    new_barcode = ""
                    if record.id:
                        new_barcode = generate_ean(self.env.company.sh_barcode_type)
                        if self.overwrite_existing:  # Overwrite existing
                            record.barcode_supp = new_barcode
                            record.generate_barcode_image_supp(new_barcode)
                        else:
                            if (
                                not record.barcode_supp
                            ):  # If barcode exists,then don't overwrite, Else generate New
                                record.barcode_supp = new_barcode
                                record.generate_barcode_image_supp(new_barcode)

            return {"type": "ir.actions.act_window_close"}

        else:
            raise UserError(_("You don't have rights to generate product barcode"))
