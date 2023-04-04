# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'ALTANMYA-PricingBasedOnBom',
    'version': '1.0',
    'summary': 'ALTANMYA-Bikar',
    'sequence': -101,
    'author': 'ALTANMYA - TECHNOLOGY SOLUTIONS',
    'company': 'ALTANMYA - TECHNOLOGY SOLUTIONS Part of ALTANMYA GROUP',
    'website': "http://tech.altanmya.net",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'sale', 'stock'],
    'description': "Bikar MRP Extension",
    'data': [
        'views/mrp_bom_views.xml',
        'views/munf_mrp_bom_views.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3'
}
