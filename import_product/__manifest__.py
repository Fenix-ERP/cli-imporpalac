{
    "name": "Import Product",
    "version": "17.0.1.0.0",
    "depends": ["base", "import_dashboard"],
    "author": "Jorge Armas",
    "category": "Tools",
    "license": "OPL-1",
    "summary": "Importa contactos desde CSV o XLSX",
    "data": [
        "security/ir.model.access.csv",
        "wizards/product_import_wizard_view.xml",
        "views/import_dashboard_menu.xml",
        "views/import_dashboard_kanban_view.xml",
    ],
    "installable": True,
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "external_dependencies": {"python": ["openpyxl"]},
}
