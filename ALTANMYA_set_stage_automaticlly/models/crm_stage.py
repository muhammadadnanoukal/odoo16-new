from odoo import api, fields, models, _, Command


class CrmStage(models.Model):
    """ Manufacturing Orders """
    _inherit = 'crm.stage'

    new_stage = fields.Boolean(string='New Stage')
    state = fields.Selection([
        ('sales_status', 'Sales Status'),
        ('manufacturing', 'Manufacturing'),
        ('operation_type_sales', 'Operation Type-Sales'),
        ('operation_type_manufacturing', 'Operation Type-Manufacturing'),

    ])
    sales_status_selection = fields.Selection([
        ('draft', "Quotation"),
        ('sent', "Quotation Sent"),
        ('tentative/final approval', 'Tentative/Final Approval'),
        ('sale', "Sales Order"),
        ('done', "Locked"),
        ('cancel', "Cancelled"),
    ])
    manufacturing_selection = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')])

    operation_type_sales = fields.Many2one('stock.picking.type', string="Operation Type-Sales")
    operation_type_manufacturing = fields.Many2one('stock.picking.type', string="Operation Type-Manufacturing")



    # @api.model
    # def create(self, vals):
    #
    #     stage = super(CrmStage, self).create(vals)
    #
    #     # stages = self.search([], order='create_date')
    #     # order = 0
    #     # for stage in stages:
    #     #     stage.write({'sequence': order})
    #     #     order += 1
    #
    #
    #     same_stage = self.env['crm.stage'].search([('state', '=', stage.state),
    #                                                ('sales_status_selection', '=', stage.sales_status_selection),
    #                                                ('manufacturing_selection', '=', stage.manufacturing_selection),
    #                                                ('id', '!=', stage.id)])
    #     pipelines = self.env['crm.lead'].search([])
    #     if len(same_stage) != 0:
    #         return stage
    #     else:
    #
    #         for pipeline in pipelines:
    #             quotations = self.env['sale.order'].search([('opportunity_id', '=', pipeline.id)])
    #
    #             #            ///////////////////////////--quotation count condition--///////////////////
    #
    #             flag = 0
    #             if len(quotations) >= 1:
    #                 new_stage = pipeline.env['crm.stage'].search(
    #                     [('state', '=', 'sales_status'), ('sales_status_selection', '=', 'draft')],
    #                     order='id desc', limit=1)
    #                 if new_stage:
    #                     pipeline.write({'stage_id': new_stage.id})
    #                     pipeline.check_status = 'compatible'
    #
    #             for quotation in quotations:
    #                 #            ///////////////////////////--quotation sent quotation --///////////////////
    #
    #                 if quotation.state == 'sent' and flag < 1:
    #                     flag = 1
    #                     new_stage = quotation.env['crm.stage'].search(
    #                         [('state', '=', 'sales_status'), ('sales_status_selection', '=', 'sent')]
    #                         , order='id desc', limit=1)
    #                     if new_stage:
    #                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                 #         ////////////////////////--quotation cancelled --/////////////////////
    #
    #                 if quotation.state == 'cancel' and flag < 2:
    #                     flag = 2
    #                     new_stage = quotation.env['crm.stage'].search(
    #                         [('state', '=', 'sales_status'), ('sales_status_selection', '=', 'cancel')]
    #                         , order='id desc', limit=1)
    #                     if new_stage:
    #                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                 #            ///////////////////////////--quotation tentative and final --///////////////////
    #
    #                 elif (quotation.state == 'tentative approval' or quotation.state == 'final approval') and flag < 3:
    #                     flag = 3
    #                     new_stage = quotation.env['crm.stage'].search([('state', '=', 'sales_status'), (
    #                         'sales_status_selection', '=', 'tentative/final approval')], order='id desc', limit=1)
    #                     if new_stage:
    #                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                 #            ///////////////////////////--quotation Sales Order --///////////////////
    #
    #                 elif quotation.state == 'sale' and flag < 4:
    #                     flag = 4
    #                     new_stage = quotation.env['crm.stage'].search(
    #                         [('state', '=', 'sales_status'), ('sales_status_selection', '=', 'sale')]
    #                         , order='id desc', limit=1)
    #                     if new_stage:
    #                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////--quotation done --///////////////////
    #
    #                 elif quotation.state == 'done' and flag < 5:
    #                     flag = 5
    #                     new_stage = quotation.env['crm.stage'].search(
    #                         [('state', '=', 'sales_status'), ('sales_status_selection', '=', 'done')]
    #                         , order='id desc', limit=1)
    #                     if new_stage:
    #                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                 #            ///////////////////////////--manufacturing draft --///////////////////
    #
    #                 delivery_transfer_ids = self.env['stock.picking'].search([('id', 'in', quotation.picking_ids.ids)])
    #                 production_ids = self.env['mrp.production'].search([('id', 'in', quotation.mrp_production_ids.ids)])
    #
    #                 for product in production_ids:
    #
    #                     if product.state == 'draft' and flag < 6:
    #                         flag = 6
    #                         new_stage = self.env['crm.stage'].search(
    #                             [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'draft')],
    #                             order='id desc', limit=1)
    #                         if new_stage:
    #                             if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                 quotation.opportunity_id.stage_id = new_stage.id
    #                                 quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////--manufacturing approve --///////////////////
    #
    #                     elif product.state == 'approve' and flag < 7:
    #                         flag = 7
    #                         new_stage = self.env['crm.stage'].search(
    #                             [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'approve')],
    #                             order='id desc', limit=1)
    #                         if new_stage:
    #                             if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                 quotation.opportunity_id.stage_id = new_stage.id
    #                                 quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////--manufacturing confirmed --///////////////////
    #
    #                     elif product.state == 'confirmed' and flag < 8:
    #                         flag = 8
    #                         new_stage = self.env['crm.stage'].search(
    #                             [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'confirmed')],
    #                             order='id desc', limit=1)
    #                         if new_stage:
    #                             if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                 quotation.opportunity_id.stage_id = new_stage.id
    #                                 quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////--manufacturing done --///////////////////
    #
    #                     elif product.state == 'done' and flag < 9:
    #                         flag = 9
    #                         new_stage = self.env['crm.stage'].search(
    #                             [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'done')],
    #                             order='id desc', limit=1)
    #                         if new_stage:
    #                             if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                 quotation.opportunity_id.stage_id = new_stage.id
    #                                 quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////--manufacturing cancel --////////////////////
    #
    #                     elif product.state == 'cancel' and flag < 10:
    #                         flag = 10
    #                         new_stage = self.env['crm.stage'].search(
    #                             [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'cancel')],
    #                             order='id desc', limit=1)
    #                         if new_stage:
    #                             if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                 quotation.opportunity_id.stage_id = new_stage.id
    #                                 quotation.opportunity_id.check_status = 'compatible'
    #
    #                     manufacture_picking_ids = self.env['stock.picking'].search([
    #                         ('group_id', '=', product.procurement_group_id.id), ('group_id', '!=', False)])
    #
    #                     #            ///////////////////////////-- operation type manufacturing --///////////////////
    #
    #                     for product_piking_id in manufacture_picking_ids:
    #                         if len(manufacture_picking_ids) != 0 and flag < 11:
    #                             list_of_stages = []
    #                             new_stage = self.env['crm.stage'].search(
    #                                 [('state', '=', 'operation_type_manufacturing'), ('operation_type_manufacturing', '=', product_piking_id.picking_type_id.id)]
    #                                 , order='id desc', limit=1)
    #                             if new_stage:
    #                                 if product_piking_id.state == 'done':
    #                                     list_of_stages.append(new_stage)
    #                                     flag = 11
    #                                     list_of_stages.append(new_stage)
    #
    #                                     if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                     #            ///////////////////////////-- operation type sales --///////////////////
    #
    #                 for delivery_transfer_id in delivery_transfer_ids:
    #                     if len(delivery_transfer_ids) != 0 and flag < 12:
    #                         if len(production_ids) == 0:
    #
    #                             new_stage = self.env['crm.stage'].search([('state', '=', 'operation_type_sales'), ('operation_type_sales', '=', delivery_transfer_id.picking_type_id.id)]
    #                                                                      , order='id desc', limit=1)
    #                             if new_stage:
    #                                 if delivery_transfer_id.state == 'done':
    #
    #                                     if quotation.opportunity_id.stage_id.id != new_stage.id:
    #                                         quotation.opportunity_id.write({'stage_id': new_stage.id})
    #                                         quotation.opportunity_id.check_status = 'compatible'
    #
    #                                         flag = 12
    #
    #     return stage
