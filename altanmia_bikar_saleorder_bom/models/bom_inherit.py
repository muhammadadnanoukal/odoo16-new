from odoo import api, fields, models, _
from odoo.osv.expression import AND


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    worked = fields.Boolean("Active Bom", default=True)

    @api.model
    def _bom_find_domain(self, products, picking_type=None, company_id=False, bom_type=False):
        domain = super(MrpBom, self)._bom_find_domain(products, picking_type, company_id, bom_type)
        if self.env.context.get("just_worked", False):
            domain = AND([domain, [('worked', '=', True)]])
        return domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['mrp.bom'].search([('product_id','=',vals['product_id']),('worked', '=', True)]).write({'worked':False})
            vals['worked'] = True

            if self.env.context.get("new_product_variant", False):
                print("new product variant asked to create")
                product = self.env['product.product'].create({'product_tmpl_id': vals['product_tmpl_id']})
                vals['product_id'] = product.id


        return super(MrpBom, self).create(vals_list)