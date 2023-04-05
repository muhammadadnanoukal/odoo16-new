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


                attr = self.env['product.attribute'].search([('name','=','BOM')], limit=1)
                if not attr:
                    attr = self.env['product.attribute'].create({'name': 'BOM'})

                variant_value = self.env['product.attribute.value'].create({
                    'name': vals['code'],
                    'attribute_id': attr.id,
                })
                attr_value_line = self.env['product.template.attribute.line'].search([('product_tmpl_id','=',vals['product_tmpl_id']), ('attribute_id','=',attr.id)])
                if not attr_value_line:
                    attr_value_line = self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': vals['product_tmpl_id'],
                        'attribute_id': attr.id,
                        'value_ids': [(6, 0, [variant_value.id ])],
                    })
                else:
                    attr_value_line.write({
                        'value_ids': [(6, 0, [variant_value.id] + attr_value_line.value_ids.ids)],
                    })
                template = self.env['product.template'].browse(vals['product_tmpl_id'])
                value = self._get_product_template_attribute_value(variant_value, template)
                product = template._get_variant_for_combination(value)
                print("new product variant asked to create", value, product, variant_value, attr_value_line)
                vals['product_id'] = product.id


        return super(MrpBom, self).create(vals_list)

    def _get_product_template_attribute_value(self, product_attribute_value, model):
        """
            Return the `product.template.attribute.value` matching
                `product_attribute_value` for self.

            :param: recordset of one product.attribute.value
            :return: recordset of one product.template.attribute.value if found
                else empty
        """

        return model.valid_product_template_attribute_line_ids.filtered(
            lambda l: l.attribute_id == product_attribute_value.attribute_id
        ).product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == product_attribute_value
        )