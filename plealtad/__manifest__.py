{
    'name': 'Programa de Lealtad',
    'version': '17.0.2.1',
    'category': 'Website',
    'summary': 'Sistema de programa de lealtad para clientes',
    'sequence': 1,
    'author': 'Gibran Quiroga',
    'website': 'https://www.mascotier.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'website_sale',
        'auth_signup',
        'loyalty',
        'portal',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/loyalty_program_data.xml',
        'views/res_partner_views.xml',
        'views/register_templates.xml',
        'views/login_templates.xml',
        'views/dashboard_templates.xml',
        'views/success_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'plealtad/static/src/scss/loyalty_style.scss',
            'plealtad/static/src/js/loyalty_forms.js'
        ],
        'web.assets_backend': [
            'plealtad/static/src/scss/loyalty_style.scss',
        ],
        'web.assets_common': [
            'plealtad/static/src/scss/loyalty_style.scss',
        ]
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}