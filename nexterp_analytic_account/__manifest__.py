# Copyright 2022 NextERP Romania SRL
# License OPL-1.0 or later

{
    "name": "Nexterp - Analytic Account",
    "version": "14.0.1.0.1",
    "category": "Localisation",
    "author": "NextERP Romania SRL",
    "website": "https://nexterp.ro",
    "support": "odoo_apps@nexterp.ro",
    "summary": """Nexterp - Analytic Account""",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "license": "OPL-1",
}
