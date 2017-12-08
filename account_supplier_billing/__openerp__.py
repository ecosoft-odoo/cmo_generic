# -*- coding: utf-8 -*-

{
    'name': "Account Supplier Billing",
    'summary': "",
    'author': "Phongyanon Y.",
    'website': "http://ecosoft.co.th",
    'category': 'Tools',
    "version": "1.0",
    'depends': [
        'account',
        'account_voucher',
        'account_auto_fy_sequence',
        'purchase_invoice_plan',
    ],
    'data': [
        'data/billing_sequence.xml',
        'security/ir.model.access.csv',
        'views/supplier_billing.xml',
        'views/voucher_payment_receipt_view.xml',
        'views/account_invoice.xml',
    ],
    'demo': [
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
