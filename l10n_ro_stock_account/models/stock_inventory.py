# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

from odoo import api, fields, models, _


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    acc_move_line_ids = fields.One2many(
        "account.move.line",
        "stock_inventory_id",
        string="Generated accounting lines",
        help="A field just to be easier to see the generated " "accounting entries ",
    )

    def post_inventory(self):
        "just to have the acc_move_line_ids used in view. can be also without this fields"
        res = super(StockInventory, self).post_inventory()
        for inv in self:
            acc_move_line_ids = self.env["account.move.line"]
            for move in inv.move_ids:
                for acc_move in move.account_move_ids:
                    acc_move_line_ids |= acc_move.line_ids
            acc_move_line_ids.write({"stock_inventory_id": inv.id})
        return res

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location']
        if self.location_ids:
            locations = self.env['stock.location'].search([('id', 'child_of', self.location_ids.ids)])
        else:
            locations = self.env['stock.location'].search(
                [('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])])
        domain = ' sq.location_id in %s AND sq.quantity != 0 AND pp.active'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']

        # If inventory by company
        if self.company_id:
            domain += ' AND sq.company_id = %s'
            args += (self.company_id.id,)
        if self.product_ids:
            domain += ' AND sq.product_id in %s'
            args += (tuple(self.product_ids.ids),)

        self.env['stock.quant'].flush(
            ['company_id', 'product_id', 'quantity', 'location_id', 'price_unit', 'lot_id', 'package_id', 'owner_id'])
        self.env['product.product'].flush(['active'])
        self.env.cr.execute("""SELECT sq.product_id, sum(sq.quantity) as product_qty, sq.price_unit, sq.location_id, sq.lot_id as prod_lot_id, sq.package_id, sq.owner_id as partner_id
            FROM stock_quant sq
            LEFT JOIN product_product pp
            ON pp.id = sq.product_id
            WHERE %s
            GROUP BY sq.product_id, sq.location_id, sq.price_unit, sq.lot_id, sq.package_id, sq.owner_id """ % domain,
                            args)
        lines = self.env.cr.dictfetchall()
        print(lines)
        for product_data in lines:
            product_data['company_id'] = self.company_id.id
            product_data['inventory_id'] = self.id
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if self.prefill_counted_quantity == 'zero':
                product_data['product_qty'] = 0
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        print(vals)
        return vals


class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    price_unit = fields.Float(
        'Unit Price',
        help="Technical field used to record the product cost set by the user "
             "during a inventory confirmation (when costing method used is "
             "'average price' or 'real'). Value given in company currency "
             "and in product uom.", copy=False)
    inventory_cost = fields.Monetary(
        string="Inventory cost",
        compute="_compute_inventory_cost",
        store=True,
        currency_field='company_currency_id'
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')

    def _check_no_duplicate_line(self):
        # Overwrite to allow multiple lines in inventory for
        # products but with different price
        for line in self:
            domain = [
                ('id', '!=', line.id),
                ('inventory_date', '=', line.inventory_date),
                ('price_unit', '=', line.price_unit),
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('partner_id', '=', line.partner_id.id),
                ('package_id', '=', line.package_id.id),
                ('prod_lot_id', '=', line.prod_lot_id.id),
                ('inventory_id', '=', line.inventory_id.id)]
            existings = self.search_count(domain)
            if existings:
                raise UserError(
                    _("There is already one inventory adjustment line "
                      "for this product, you should rather modify this "
                      "one instead of creating a new one."))

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id',
                  'price_unit')
    def _onchange_quantity_context(self):
        product_qty = False
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
        if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
            theoretical_qty = self.product_id.with_context(price_unit=self.price_unit).get_theoretical_quantity(
                self.product_id.id,
                self.location_id.id,
                lot_id=self.prod_lot_id.id,
                package_id=self.package_id.id,
                owner_id=self.partner_id.id,
                to_uom=self.product_uom_id.id,
            )
        else:
            theoretical_qty = 0
        # Sanity check on the lot.
        if self.prod_lot_id:
            if self.product_id.tracking == 'none' or self.product_id != self.prod_lot_id.product_id:
                self.prod_lot_id = False

        if self.prod_lot_id and self.product_id.tracking == 'serial':
            # We force `product_qty` to 1 for SN tracked product because it's
            # the only relevant value aside 0 for this kind of product.
            self.product_qty = 1
        elif self.product_id and float_compare(self.product_qty, self.theoretical_qty,
                                               precision_rounding=self.product_uom_id.rounding) == 0:
            # We update `product_qty` only if it equals to `theoretical_qty` to
            # avoid to reset quantity when user manually set it.
            self.product_qty = theoretical_qty
        self.theoretical_qty = theoretical_qty

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()
        res = super(StockInventoryLine, self)._get_move_values(
            qty, location_id, location_dest_id, out)
        res['price_unit'] = self.price_unit
        return res

    @api.depends("product_qty", "price_unit")
    def _compute_inventory_cost(self):
        for record in self:
            record.inventory_cost = \
                record.product_qty * record.price_unit

    def _generate_moves(self):
        vals_list = []
        for line in self:
            virtual_location = line._get_virtual_location()
            rounding = line.product_id.uom_id.rounding
            if float_is_zero(line.difference_qty, precision_rounding=rounding):
                continue
            if line.difference_qty > 0:  # found more than expected
                vals = line.with_context(price_unit=line.price_unit)._get_move_values(line.difference_qty, virtual_location.id, line.location_id.id, False)
            else:
                vals = line.with_context(price_unit=line.price_unit)._get_move_values(abs(line.difference_qty), line.location_id.id, virtual_location.id, True)
            vals_list.append(vals)
        return self.env['stock.move'].create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to handle the case we create inventory line without
        `theoretical_qty` because this field is usually computed, but in some
        case (typicaly in tests), we create inventory line without trigger the
        onchange, so in this case, we set `theoretical_qty` depending of the
        product's theoretical quantity.
        Handles the same problem with `product_uom_id` as this field is normally
        set in an onchange of `product_id`.
        Finally, this override checks we don't try to create a duplicated line.
        """
        for values in vals_list:
            if 'theoretical_qty' not in values and 'price_unit' in values:
                theoretical_qty = self.env['product.product'].with_context(
                    price_unit=values.get('price_unit')).get_theoretical_quantity(
                    values['product_id'],
                    values['location_id'],
                    lot_id=values.get('prod_lot_id'),
                    package_id=values.get('package_id'),
                    owner_id=values.get('partner_id'),
                    to_uom=values.get('product_uom_id'),
                )
                values['theoretical_qty'] = theoretical_qty
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        res = super(StockInventoryLine, self).create(vals_list)
        res._check_no_duplicate_line()
        return res
