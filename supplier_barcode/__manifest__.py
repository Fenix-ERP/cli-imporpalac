{
    "name": "Supplier Barcode Generator",
    "author": "Santiago Illapa / FenixERP",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "summary": "Default Make Barcode Module Supplier Product Barcode Generate",
    "long_description": """
    Currently in odoo barcode number not auto-generated in the product,
    our module help to the generated barcode for the product.
    You can also create/update mass product barcodes.
    you can also choose different barcode types.""",
    "depends": [
        "product",
        "base_setup",
        "sale_management",
        "sh_barcode_generator_simple",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
    ],
    "installable": True,
    "license": "OPL-1",
    "auto_install": False,
    "application": True,
    "price": 12,
    "currency": "EUR",
}
