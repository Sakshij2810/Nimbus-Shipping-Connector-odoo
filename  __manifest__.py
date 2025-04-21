{
    'name': 'Nimbus Shipping Connector',
    'version': '1.0.0',
    'summary': 'Integration with Nimbus Shipping API',
    'description': """
        This module integrates Odoo with Nimbus Shipping services.
        Features include:
        - Real-time shipping rates
        - Label generation
        - Shipment tracking
        - Automatic manifest generation
    """,
    'author': 'Wisteria',
    'website': 'https://www.wisteriajewels.com/',
    'category': 'Inventory/Delivery',
    'depends': ['delivery', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_views.xml',
        'views/templates.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}