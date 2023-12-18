# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from collections import defaultdict
from dateutil.relativedelta import relativedelta


_interval = {
    '15': lambda count: relativedelta(days=count*15),
    '30': lambda count: relativedelta(days=count*30),
    '90': lambda count: relativedelta(days=count*90),
    '180': lambda count: relativedelta(days=count*180),
    '365': lambda count: relativedelta(days=count*365)
}

NUMBER_INTERVALS = 6

class SVLAgeReportLocation(models.TransientModel):
    _name = 'l10n.ro.svl.age.report.location'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    report_id = fields.Many2one(
        'l10n.ro.svl.age.report',
        string='Report',
    )


class SVLAgeReport(models.TransientModel):
    _name = 'l10n.ro.svl.age.report'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', "Related product", check_company=True)
    date_ref = fields.Date("Reference Date", default=fields.Date.today)

    interval_days = fields.Selection(string="Days", selection=[('15', '15 days'), ('30', '30 days'), ('90', '90 days'), ('180', '180 days'), ('365', '365 days')], default="15")

    location_ids = fields.One2many(
        'l10n.ro.svl.age.report.location',
        'report_id',
        string='Locations',
        compute="_compute_location_ids",
        store=True
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        required=True,
        string="Warehouse",
        readonly=False,
        help="Warehouse to consider for the route selection",
    )
    line_ids = fields.One2many(
        'l10n.ro.svl.age.report.line',
        'report_id',
        string='Report Lines',
    )

    def name_get(self):
        res = []
        for rep in self:
            name = "Stock Age Report: {} (interval: {})".format(
                rep.date_ref, dict(self._fields["interval_days"].selection).get(rep.interval_days)
            )
            res.append((rep.id, name))
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)],
            limit=1
        )
        res['warehouse_id'] = warehouse.id
        return res

    @api.depends('warehouse_id')
    def _compute_location_ids(self):
        self.location_ids = [(6, 0, [])]

        locs = self.env['stock.location'].search([('usage', '=', 'internal')], order="id")
        locs = locs.filtered(lambda l: l.get_warehouse() == self.warehouse_id)
        location_ids = []
        idx = 10
        for loc in locs:
            location_ids.append((0, 0, {
                'sequence': idx, 'location_id': loc.id
            }))
            idx += 10
        self.location_ids = location_ids

    def do_compute_report(self):
        if self.product_id:
            products = self.product_id
        else:
            products = self.product_id or self.env['product.product'].search([])
        locations = self.location_ids.mapped('location_id')

        self._run_aged_inventory(products, locations.ids)

        return True

    def _run_aged_inventory(self, products, locations):
        self = self.sudo()

        def _to_str(date):
            return fields.Date.to_string(date)

        date_ref = date_ref_next = fields.Date.from_string(self.date_ref)
        svl_date_from = _to_str(date_ref)
        svl_date_to = _to_str(date_ref - relativedelta(days=(NUMBER_INTERVALS-1)*int(self.interval_days)))
        domain = ['&',
                        ('product_id', 'in', products.ids),
                        '&',
                            ('create_date', '<=', svl_date_from),
                            '|',
                                ('l10n_ro_location_dest_id', 'in', locations),
                                ('l10n_ro_location_id', "in", locations),
                   ]
        products = self.env['stock.valuation.layer'].search(domain).mapped('product_id')

        dict1 = {}
        age_list = []
        if len(products.ids) == 1:

            self.env.cr.execute('''
            select product_id as product_id, sum(quantity) as quantity, sum(value) as value
                from stock_valuation_layer
                where product_id = %s and create_date::date<='%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s)
                group by product_id''' % (products.id, svl_date_to, tuple(locations+[0]), tuple(locations+[0])))
        else:
            self.env.cr.execute('''
            select product_id as product_id,sum(quantity) as quantity, sum(value) as value
                from stock_valuation_layer
                where product_id in %s and create_date::date<='%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s)
                group by product_id''' % (tuple(products.ids), svl_date_to, tuple(locations+[0]), tuple(locations+[0])))
        product_dicts = self.env.cr.dictfetchall()
        product_dicts = dict((item['product_id'], item) for item in product_dicts)

        for product in products:
            days = 0
            age_list = []
            for i in range(NUMBER_INTERVALS):
                date = date_ref - _interval[self.interval_days](i)
                age_list.append({
                    'date': date,
                    'quantity': 0,
                    'value': 0,
                })

                days_next = (date_ref - (date_ref - _interval[self.interval_days](i + 1))).days
                name = f'{days} - {days_next}'
                if i == NUMBER_INTERVALS - 1:
                    name += '+'
                age_list[i]['name'] = f'[{i+1}] {name} ' + _('days')
                days = days_next
            product_dict = product_dicts.setdefault(product.id, {'product_id': product.id, 'quantity': 0, 'value': 0})
            if product_dict['quantity']:
                quantity_svl = round(product_dict['quantity'], 2)
                value_svl = round(product_dict['value'], 2)
                age_list[NUMBER_INTERVALS - 1]['quantity'] = max(0, quantity_svl)
                age_list[NUMBER_INTERVALS - 1]['value'] = max(0, value_svl)
            if product.l10n_ro_property_stock_valuation_account_id:
                account_id = product.l10n_ro_property_stock_valuation_account_id.id
            else:
                account_id = product.categ_id.property_stock_valuation_account_id.id
            dict1[product] = {'age_list': age_list,
                              'account_id': account_id,
                              'product_id': product.id}

        # for interval_nb in [4, 3, 2, 1, 0]
        for interval_nb in reversed(range(NUMBER_INTERVALS - 1)):
            period_date_from = age_list[interval_nb]['date']
            period_date_to = age_list[interval_nb + 1]['date']
            domain_in = [
                       ('product_id', 'in', products.ids),
                       ('create_date', '<=', period_date_from),
                       ('create_date', '>', period_date_to),
                       ('l10n_ro_location_dest_id', 'in', locations),
                       ('quantity', '>=', 0.000),
                       ('l10n_ro_valued_type', "!=", 'internal_transfer'),
                       ]

            domain_out = [
                       ('product_id', 'in', products.ids),
                       ('create_date', '<=', period_date_from),
                       ('create_date', '>', period_date_to),
                       ('l10n_ro_location_id', "in", locations),
                       ('quantity', '<', 0.000),
                       ('l10n_ro_valued_type', "!=", 'internal_transfer'),
                       ]
            svls_in = self.env['stock.valuation.layer'].\
                read_group(domain=domain_in,
                           fields=['quantity:sum',
                                   'value:sum'],
                           groupby=['product_id'],
                           lazy=False)
            svls_out = self.env['stock.valuation.layer'].\
                read_group(domain=domain_out,
                           fields=['quantity:sum',
                                   'value:sum'],
                           groupby=['product_id'],
                           lazy=False)
            if svls_in:
                for svl_in in svls_in:
                    product = self.env['product.product'].browse(svl_in.get('product_id')[0])
                    dict1[product]['age_list'][interval_nb]['quantity'] = svl_in.get('quantity')
                    dict1[product]['age_list'][interval_nb]['value'] = svl_in.get('value')
                    remaining_qty_initial = sum([item['quantity'] for item in dict1[product]['age_list'][interval_nb:]])
                    if remaining_qty_initial == 0:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            item['quantity'] = 0
                            item['value'] = 0
            if svls_out:
                for svl_out in svls_out:
                    product = self.env['product.product'].browse(svl_out.get('product_id')[0])
                    remaining_qty_initial = sum([item['quantity'] for item in dict1[product]['age_list'][interval_nb:]])
                    remaining_value_initial = sum([item['value'] for item in dict1[product]['age_list'][interval_nb:]])
                    remaining_qty = remaining_qty_initial - abs(svl_out.get('quantity'))
                    remaining_value = remaining_value_initial - abs(svl_out.get('value'))
                    if remaining_qty_initial == 0:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            item['quantity'] = 0
                            item['value'] = 0
                    elif remaining_qty < 0:
                        dict1[product]['age_list'][interval_nb]['quantity'] = remaining_qty
                        dict1[product]['age_list'][interval_nb]['value'] = remaining_value
                        for item in dict1[product]['age_list'][interval_nb+1:]:
                            item['quantity'] = 0
                            item['value'] = 0
                    else:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            if remaining_qty == 0:
                                item['quantity'] = 0
                                item['value'] = 0
                                continue
                            if item['quantity'] > remaining_qty:
                                item['quantity'] = remaining_qty
                                item['value'] = remaining_value
                                remaining_qty = 0
                                remaining_value = 0
                            else:
                                remaining_qty -= item['quantity']
                                remaining_value -= item['value']

        # create report lines
        for product_dict in dict1:
            query = '''INSERT INTO l10n_ro_svl_age_report_line
            (report_id, name, date, product_id, account_id, quantity, value)
                VALUES '''
            for index, age_list in enumerate(dict1[product_dict]['age_list']):

                if dict1[product_dict]['account_id']:
                    query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', {dict1[product_dict]['product_id']}," \
                           f" {dict1[product_dict]['account_id']}, {age_list['quantity']}, { 0 if age_list['quantity'] == 0 else age_list['value']})"
                else:
                    query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', {dict1[product_dict]['product_id']}," \
                           f" NULL, {age_list['quantity']}, { 0 if age_list['quantity'] == 0 else age_list['value']})"
                if index == NUMBER_INTERVALS-1:
                    query += ';'
                else:
                    query += ','
            self.env.cr.execute(query)

    def button_show_sheet(self):
        self.do_compute_report()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_stock_age_report.action_sheet_age_report_line"
        )

        action["display_name"] = "{} {} ({})".format(
            action["name"],
            self.date_ref,
            self.interval_days
        )
        action["domain"] = [("report_id", "=", self.id)]
        action["target"] = "main"
        return action

class SVLAgeReportLine(models.TransientModel):
    _name = 'l10n.ro.svl.age.report.line'
    _order = 'date desc'

    report_id = fields.Many2one("l10n.ro.svl.age.report", readonly=True)
    name = fields.Char(string='Days Range', readonly=True)
    date = fields.Date(readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    internal_reference = fields.Char(
        "Internal Reference", related="product_id.default_code",
        stored=True,
        readonly=True)
    product_uom = fields.Many2one(
        "uom.uom", string="UM", related="product_id.uom_id", readonly=True,
        stored=True
    )
    account_id =fields.Many2one('account.account', readonly=True)
    quantity = fields.Float("Quantity", readonly=True)
    value = fields.Float("Value", readonly=True)
