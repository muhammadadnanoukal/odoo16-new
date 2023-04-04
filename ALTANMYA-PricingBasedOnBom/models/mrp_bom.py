from odoo.osv.expression import AND
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND, NEGATIVE_TERM_OPERATORS
from odoo.tools import float_round
import inspect
from collections import defaultdict


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    code = fields.Char('Reference')
    type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Kit'),
        ('assembled', 'Assembled Products'),
        ('normalWithPrice', 'Priced Manufactured products'),
    ], 'BoM Type',
        default="normal", required=True)

    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=False)

    pricing_type_square = fields.Boolean('Square Meter', default=True, )
    pricing_type_component = fields.Boolean('Component', default=False, )

    def read(self, fields=None, load='_classic_read'):
        self.code = self.product_tmpl_id.name
        return super().read(fields, load)

    # @api.model
    # def create(self, vals):
    #     custom_code = self._context['default_name']
    #     if vals.get('product_tmpl_id'):
    #         vals['code'] = custom_code
    #     return super(MrpBom, self).create(vals)

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            if self.product_id.product_tmpl_id != self.product_tmpl_id:
                self.product_id = False
            self.bom_line_ids.bom_product_template_attribute_value_ids = False
            self.operation_ids.bom_product_template_attribute_value_ids = False
            self.byproduct_ids.bom_product_template_attribute_value_ids = False

            domain = [('product_tmpl_id', '=', self.product_tmpl_id.id)]
            if self.id.origin:
                domain.append(('id', '!=', self.id.origin))
        self.code = self._context['default_name']

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        for line in self.bom_line_ids:
            if line.product_id:
                line.price_unit = line.compute_price_unit()

    total_amount = fields.Float('Total Amount', compute='_compute_amount', store=True, tracking=True)

    @api.depends('bom_line_ids.price_unit', 'bom_line_ids.product_qty', 'bom_line_ids.price_subtotal')
    def _compute_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.bom_line_ids.mapped('price_subtotal'))

    @api.model
    def _bom_find(self, products, picking_type=None, company_id=False, bom_type=False, bom_ids=False):
        if not bom_ids:
            return super(MrpBom, self)._bom_find(products, picking_type, company_id, bom_type)
        else:
            bom_by_product = defaultdict(list)
            products = products.filtered(lambda p: p.type != 'service')
            if not products:
                return bom_by_product
            domain = self._bom_find_domain(products, picking_type=picking_type, company_id=company_id,
                                           bom_type=bom_type, bom_ids=bom_ids)
            # Performance optimization, allow usage of limit and avoid the for loop `bom.product_tmpl_id.product_variant_ids`
            if len(products) == 1:
                bom = self.search(domain, order='sequence, product_id, id')
                if bom:
                    bom_by_product[products] = bom
                return bom_by_product

            boms = self.search(domain, order='sequence, product_id, id')
            products_ids = set(products.ids)
            for bom in boms:
                products_implies = bom.product_id or bom.product_tmpl_id.product_variant_ids
                for product in products_implies:
                    if product.id in products_ids:
                        bom_by_product[product].append(bom)
            return bom_by_product

    @api.model
    def _bom_find_domain(self, products, picking_type=None, company_id=False, bom_type=False, bom_ids=False):
        domain = ['|', ('product_id', 'in', products.ids), '&', ('product_id', '=', False),
                  ('product_tmpl_id', 'in', products.product_tmpl_id.ids)]
        if company_id or self.env.context.get('company_id'):
            domain = AND([domain, ['|', ('company_id', '=', False),
                                   ('company_id', '=', company_id or self.env.context.get('company_id'))]])
        if picking_type:
            domain = AND([domain, ['|', ('picking_type_id', '=', picking_type.id), ('picking_type_id', '=', False)]])
        if bom_type:
            op = ''
            if bom_type == ['phantom', 'assembled']:
                op = 'in'
            else:
                op = '='
            domain = AND([domain, [('type', op, bom_type)]])
        if bom_ids:
            domain = AND([domain, [('id', 'in', bom_ids)]])
        return domain

    def explode(self, product, quantity, bom_ids=False, picking_type=False):

        """
            Explodes the BoM and creates two lists with all the information you need: bom_done and line_done
            Quantity describes the number of times you need the BoM: so the quantity divided by the number created by the BoM
            and converted into its UoM
        """
        from collections import defaultdict

        graph = defaultdict(list)
        V = set()

        def check_cycle(v, visited, recStack, graph):
            visited[v] = True
            recStack[v] = True
            for neighbour in graph[v]:
                if visited[neighbour] == False:
                    if check_cycle(neighbour, visited, recStack, graph) == True:
                        return True
                elif recStack[neighbour] == True:
                    return True
            recStack[v] = False
            return False

        product_ids = set()
        product_boms = {}

        def update_product_boms():
            products = self.env['product.product'].browse(product_ids)
            product_boms.update(self._bom_find(products, picking_type=picking_type or self.picking_type_id,
                                               company_id=self.company_id.id, bom_type=['phantom', 'assembled'],
                                               bom_ids=bom_ids))
            # Set missing keys to default value
            for product in products:
                product_boms.setdefault(product, self.env['mrp.bom'])

        boms_done = [(self, {'qty': quantity, 'product': product, 'original_qty': quantity, 'parent_line': False})]
        lines_done = []
        V |= set([product.product_tmpl_id.id])

        bom_lines = []
        for bom_line in self.bom_line_ids:
            product_id = bom_line.product_id
            V |= set([product_id.product_tmpl_id.id])
            graph[product.product_tmpl_id.id].append(product_id.product_tmpl_id.id)
            bom_lines.append((bom_line, product, quantity, False))
            product_ids.add(product_id.id)
        update_product_boms()
        product_ids.clear()
        while bom_lines:
            current_line, current_product, current_qty, parent_line = bom_lines[0]
            bom_lines = bom_lines[1:]

            if current_line._skip_bom_line(current_product):
                continue

            line_quantity = current_qty * current_line.product_qty
            if not current_line.product_id in product_boms:
                update_product_boms()
                product_ids.clear()
            boms = product_boms.get(current_line.product_id)
            if boms:
                try:
                    for bom in boms:
                        converted_line_quantity = current_line.product_uom_id._compute_quantity(
                            line_quantity / bom.product_qty, bom.product_uom_id)
                        bom_lines += [(line, current_line.product_id, converted_line_quantity, current_line) for line in
                                      bom.bom_line_ids]
                        for bom_line in bom.bom_line_ids:
                            graph[current_line.product_id.product_tmpl_id.id].append(
                                bom_line.product_id.product_tmpl_id.id)
                            if bom_line.product_id.product_tmpl_id.id in V and check_cycle(
                                    bom_line.product_id.product_tmpl_id.id, {key: False for key in V},
                                    {key: False for key in V}, graph):
                                raise UserError(
                                    _('Recursion error!  A product with a Bill of Material should not have itself in its BoM or child BoMs!'))
                            V |= set([bom_line.product_id.product_tmpl_id.id])
                            if not bom_line.product_id in product_boms:
                                product_ids.add(bom_line.product_id.id)
                        boms_done.append((bom, {'qty': converted_line_quantity, 'product': current_product,
                                                'original_qty': quantity, 'parent_line': current_line}))
                except:
                    converted_line_quantity = current_line.product_uom_id._compute_quantity(
                        line_quantity / boms.product_qty, boms.product_uom_id)
                    bom_lines += [(line, current_line.product_id, converted_line_quantity, current_line) for line in
                                  boms.bom_line_ids]
                    for bom_line in boms.bom_line_ids:
                        graph[current_line.product_id.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
                        if bom_line.product_id.product_tmpl_id.id in V and check_cycle(
                                bom_line.product_id.product_tmpl_id.id, {key: False for key in V},
                                {key: False for key in V}, graph):
                            raise UserError(
                                _('Recursion error!  A product with a Bill of Material should not have itself in its BoM or child BoMs!'))
                        V |= set([bom_line.product_id.product_tmpl_id.id])
                        if not bom_line.product_id in product_boms:
                            product_ids.add(bom_line.product_id.id)
                    boms_done.append((boms, {'qty': converted_line_quantity, 'product': current_product,
                                             'original_qty': quantity, 'parent_line': current_line}))
            else:
                # We round up here because the user expects that if he has to consume a little more, the whole UOM unit
                # should be consumed.
                rounding = current_line.product_uom_id.rounding
                line_quantity = float_round(line_quantity, precision_rounding=rounding, rounding_method='UP')
                lines_done.append((current_line,
                                   {'qty': line_quantity, 'product': current_product, 'original_qty': quantity,
                                    'parent_line': parent_line}))

        return boms_done, lines_done

    total_installation_date = fields.Float('Total Installation Date', compute='_compute_installation_amount',
                                           store=True, tracking=True)

    @api.depends('bom_line_ids.estimated_installation_date')
    def _compute_installation_amount(self):
        for rec in self:
            rec.total_installation_date = sum(rec.bom_line_ids.mapped('estimated_installation_date'))


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    # bom_id = fields.Many2one(
    #     'mrp.bom', 'Parent BoM',
    #     index=True, ondelete='cascade', required=True)
    # product_id = fields.Many2one('product.product', 'Component', required=True, check_company=True)
    # product_id = fields.Many2one('product.product', 'Component', required=True, check_company=True,
    #                              domain="[('toto', '=', bom_id.pricing_type_square),('toto', '=', True)]")

    last_price = fields.Float(string='Last Price')
    estimated_installation_date = fields.Float(string='Estimated Installation Date', readonly=True, store=True, )
    attachments_count = fields.Integer(string='Attachment Count', compute='_compute_attachments_count')

    @api.onchange('estimated_installation_date')
    def teafgasf(self):
        print('hello', self.bom_id.pricing_type_square)
        print('bvncm,x.;;clkvjnbvmc,x./')
        print(self.bom_id.pricing_type_square)
        print(self.product_id.product_tmpl_id.pricing_type_square_tmpl)
        if self.product_id.pricing_type_square_tmpl == self.bom_id.pricing_type_square:
            print('done 1')
        else:
            print('nop 1')

    @api.onchange('product_id', 'product_qty')
    def _compute_installation_date(self):
        res = self.product_id.product_tmpl_id.estimated_installation_date_tmpl * self.product_qty
        self.estimated_installation_date = res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Compute Last Price
            self._cr.execute(
                'SELECT price FROM product_supplierinfo WHERE product_tmpl_id = {} ORDER BY id DESC LIMIT 1'.format(
                    self.product_id.product_tmpl_id.id)
            )
            _res = self._cr.dictfetchall()
            if _res is not None and len(_res) != 0:
                self.last_price = _res[0].get('price')
            else:
                self.last_price = 0
            # Compute Price Unit
            self.price_unit = self.compute_price_unit()

    def compute_price_unit(self):
        price_unit = 0.0
        from_pricelist = self.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
             ('pricelist_id', '=', self.bom_id.pricelist_id.id)], limit=1)
        if not from_pricelist:
            from_template = self.env['product.template'].search([('id', '=', self.product_id.product_tmpl_id.id)],
                                                                limit=1)
            if from_template:
                price_unit = from_template.list_price
        else:
            price_unit = from_pricelist.fixed_price

        return price_unit

    price_unit = fields.Float('Unit Price', required=True, default=0.0)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', default=0.0)

    @api.depends('price_unit', 'product_qty')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.product_qty

    check_field = fields.Boolean('Check', compute='get_user')

    @api.depends('price_unit')
    def get_user(self):
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            self.check_field = False
        else:
            self.check_field = True
