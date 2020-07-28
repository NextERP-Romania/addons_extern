# Copyright 2014-2018 Tecnativa - Pedro M. Baeza
# Copyright 2015 Antonio Espinosa - Tecnativa <antonio.espinosa@tecnativa.com>
# Copyright 2016 Carlos Dauden - Tecnativa <carlos.dauden@tecnativa.com>
# Copyright 2016 Luis M. Ontalba - Tecnativa <luis.martinez@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPickingForPurchase(models.Model):
    _inherit = "stock.picking"

    purchase_id = fields.Many2one('purchase.order',readonly=1,string="Created by this purchase")  # or lile om sa;e tp be related to procurmet group? 
    purchase_currency_id = fields.Many2one(related="purchase_id.currency_id", readonly=1, string="Purchase Currency", related_sudo=True,  )

    def _compute_amount_all(self):
        """overwrite of function from stock_picking to take into account also the purchase
        This is computed with sudo for avoiding problems if you don't have
        access to sales orders (stricter warehouse users, inter-company
        records...).
        """
        for pick in self:
            if pick.sale_id:
                super()._compute_amount_all()
            else:
                round_curr = pick.purchase_id.currency_id.round
                amount_tax = 0.0
                for tax_group in pick.get_taxes_values_purchase().values():
                    amount_tax += round_curr(tax_group["amount"])
                amount_untaxed = sum([l.purchase_price_subtotal for l in pick.move_line_ids])
                pick.update(
                    {
                        "amount_untaxed": amount_untaxed,
                        "amount_tax": amount_tax,
                        "amount_total": amount_untaxed + amount_tax,
                    }
                )

    def get_taxes_values_purchase(self):
        tax_grouped = {}
        for line in self.move_line_ids:
            for tax in line.purchase_line.taxes_id:
                tax_id = tax.id
                if tax_id not in tax_grouped:
                    tax_grouped[tax_id] = {"base": line.purchase_price_subtotal, "tax": tax}
                else:
                    tax_grouped[tax_id]["base"] += line.purchase_price_subtotal
        for tax_id, tax_group in tax_grouped.items():
            tax_grouped[tax_id]["amount"] = tax_group["tax"].compute_all(
                tax_group["base"], self.purchase_id.currency_id)["taxes"][0]["amount"]
        return tax_grouped
