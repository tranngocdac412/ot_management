{
    'name': 'OT Management',
    'version': '1.0',
    'depends': ['base', 'hr', 'project', 'mail'],
    'author': 'D',
    'category': '',
    'description': 'OT Management',
    'data': [
        'security/ir.model.access.csv',

        'views/ot_registration.xml',
        'views/ot_request.xml',

        'views/menu.xml'
    ],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
    'sequence': 1
}