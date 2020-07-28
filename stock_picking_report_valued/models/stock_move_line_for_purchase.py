# Copyright 2014-2018 Tecnativa - Pedro M. Baeza
# Copyright 2015 Antonio Espinosa - Tecnativa <antonio.espinosa@tecnativa.com>
# Copyright 2018 Luis M. Ontalba - Tecnativa <luis.martinez@tecnativa.com>
# Copyright 2016-2018 Carlos Dauden - Tecnativa <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import ValidationError

# creating some fields to have also valued purchases 

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    purchase_line = fields.Many2one(related="move_id.purchase_line_id",  string="Related purchase line")
    purchase_currency_id = fields.Many2one(related="purchase_line.currency_id",  string="Purchase Currency")
    purchase_tax_id = fields.Many2many(related="purchase_line.taxes_id",  string="Purchase Tax")
    purchase_price_unit = fields.Float(related="purchase_line.price_unit",  string="Purchase price unit")
    purchase_tax_description = fields.Char(
        compute="_compute_purchase_order_line_fields",
        string="Purchase Tax Description", compute_sudo=True,  # See explanation for sudo in compute method
    )
    purchase_price_subtotal = fields.Monetary(
        compute="_compute_purchase_order_line_fields",
        string="Purchase Price subtotal", compute_sudo=True,)
    purchase_price_tax = fields.Float(
        compute="_compute_purchase_order_line_fields", string="Purchase Taxes", compute_sudo=True)
    purchase_price_total = fields.Monetary(
        compute="_compute_purchase_order_line_fields", string="Purchase Total", compute_sudo=True)

    def _compute_purchase_order_line_fields(self):
        """This is computed with sudo for avoiding problems if you don't have
        access to purchase orders (stricter warehouse users, inter-company
        records...).
        """
        for line in self:
            purchase_line = line.purchase_line
            price_unit = (
                purchase_line.price_subtotal / purchase_line.product_uom_qty
                if purchase_line.product_uom_qty
                else purchase_line.price_reduce
            )
            taxes = line.purchase_tax_id.compute_all(
                price_unit=price_unit,
                currency=line.currency_id,
                quantity=line.qty_done or line.product_qty,
                product=line.product_id,
                partner=purchase_line.order_id.partner_id,
            )
            if purchase_line.company_id.tax_calculation_rounding_method == "round_globally":
                price_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))
            else:
                price_tax = taxes["total_included"] - taxes["total_excluded"]
            line.update(
                {
                    "purchase_tax_description": ", ".join(
                        t.name or t.description for t in line.purchase_tax_id
                    ),
                    "purchase_price_subtotal": taxes["total_excluded"],
                    "purchase_price_tax": price_tax,
                    "purchase_price_total": taxes["total_included"],
                }
            )
    
    def _get_aggregated_product_quantities(self, **kwargs):
        """giving also the purchase_price needed for showing in report
        this function is used in aggregated lines template 
        """
        if self.picking_id.sale_id:
            return super()._get_aggregated_product_quantities(**kwargs)
        elif self.picking_id.purchase_id:
            "rewrite of function "
            aggregated_move_lines = {}
            for move_line in self:
                name = move_line.product_id.display_name
                description = move_line.move_id.description_picking
                if description == name or description == move_line.product_id.name:
                    description = False
                uom = move_line.product_uom_id
                line_key = str(move_line.product_id.id) + "_" + name + (description or "") + "uom " + str(uom.id)
    
                if line_key not in aggregated_move_lines:
                    aggregated_move_lines[line_key] = {'name': name,
                                                       'description': description,
                                                       'qty_done': move_line.qty_done,
                                                       'product_uom': uom.name,
                                                       'product': move_line.product_id,
                                                        # added by us
                                                        'purchase_price_unit': move_line.purchase_price_unit,
                                                       'purchase_tax_description': move_line.purchase_tax_description,
                                                       'purchase_price_subtotal': move_line.purchase_price_subtotal,
                                                       'purchase_price_tax': move_line.purchase_price_tax,
                                                       }
                else:
                    aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done
                    # added by us
                    aggregated_move_lines[line_key]['purchase_price_subtotal'] += move_line.purchase_price_subtotal
                    aggregated_move_lines[line_key]['purchase_price_tax'] += move_line.purchase_price_tax
                
            return aggregated_move_lines
        return {}

         
       