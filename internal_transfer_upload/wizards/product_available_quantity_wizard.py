# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
# pylint: skip-file
from odoo import fields, models,api


class ProductAvailableQuantityImporpaWizard(models.TransientModel):
    _name = "product.available.quantity.wizard.imporpa"
    _description = "Product Available Quantity Wizard"

    stock_quant_ids = fields.Many2many("stock.quant")
    product_product_id = fields.Many2one("product.product", string="Product Name")

    
    @api.model
    def default_get(self, fields):
        res = super(ProductAvailableQuantityImporpaWizard, self).default_get(fields)
        
        # Obtener el contexto - ahora desde stock.move (líneas de picking)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')
        
        product_list = []
        product_id = False
        
        if active_model == 'stock.move':
            stock_move = self.env['stock.move'].browse(active_id)
            product_id = stock_move.product_id.id
            
            stock_quant_obj = self.env['stock.quant']
            stock_quant_search_ids = stock_quant_obj.search([
                ('product_id', '=', product_id),
                ('location_id.usage', '=', 'internal'),
            ])
            
            for record in stock_quant_search_ids:
                product_list.append(record.id)
                
        elif active_model == 'stock.picking':
            picking = self.env['stock.picking'].browse(active_id)
            if picking.move_ids_without_package and picking.move_ids_without_package[0].product_id:
                product_id = picking.move_ids_without_package[0].product_id.id
                
                stock_quant_obj = self.env['stock.quant']
                stock_quant_search_ids = stock_quant_obj.search([
                    ('product_id', '=', product_id),
                    ('location_id.usage', '=', 'internal'),
                ])
                
                for record in stock_quant_search_ids:
                    product_list.append(record.id)

        res.update({
            'product_product_id': product_id,
            'stock_quant_ids': [(6, 0, product_list)],
        })
        return res
