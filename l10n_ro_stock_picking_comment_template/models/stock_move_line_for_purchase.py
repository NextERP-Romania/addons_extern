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

    list_price = fields.Float( related="product_id.list_price")    
    margin = fields.Float(string='Margin [%]', compute="_compute_sale_order_line_fields", compute_sudo=True)
    sale_with_margin_price_total = fields.Float(compute="_compute_sale_order_line_fields", compute_sudo=True)


    def _compute_purchase_order_line_fields(self):
        """to put aso the margin and sale_with_margin_price
        """
        for line in self:
            margin = 0
            sale_with_margin_price_total = 0
            if 'purchase_price_unit' in  self._fields and 'purchase_line' in  self._fields:
                # means that the stock_picking report is installed
                super()._compute_purchase_order_line_fields() # the before behavior 
                margin = (line.list_price - line.purchase_price_unit)/100
                taxes = self.product_id.taxes_id.compute_all(
                    price_unit=line.purchase_price_unit,
                   # currency=line.currency_id,  line.purchase_currency_id
                    quantity=line.qty_done or line.product_qty,
                    product=line.product_id,
                    #partner=,
                )
                sale_with_margin_price_total = taxes["total_included"]
            line.update(
                {
                    "margin": margin,
                    "sale_with_margin_price_total": sale_with_margin_price_total,
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
                                    "margin": move_line.margin,
                                    "sale_with_margin_price_total": move_line.sale_with_margin_price_total,

                                                       }

                else:
                    aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done
                    # added by us
                    aggregated_move_lines[line_key]['purchase_price_subtotal'] += move_line.purchase_price_subtotal
                    aggregated_move_lines[line_key]['purchase_price_tax'] += move_line.purchase_price_tax
                    #now
                    aggregated_move_lines[line_key]['margin'] += move_line.margin
                    aggregated_move_lines[line_key]['sale_with_margin_price_total'] += move_line.sale_with_margin_price_total
                    
                
            return aggregated_move_lines
        return {}

         
       