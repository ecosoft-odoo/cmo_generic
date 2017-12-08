# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp import tools


class StockLocationView(models.Model):
    # This class is solely for PABI2
    _name = 'stock.location.view'
    _auto = False

    name = fields.Char(
        string='Name',
    )
    usage = fields.Selection(
        [('supplier', 'Supplier Location'),
         ('view', 'View'),
         ('internal', 'Internal Location'),
         ('customer', 'Customer Location'),
         ('inventory', 'Inventory'),
         ('procurement', 'Procurement'),
         ('production', 'Production'),
         ('transit', 'Transit Location')],
        string='Location Type',
    )
    active = fields.Boolean(
        string='Active',
    )
    location_id = fields.Many2one(
        'stock.location.view',
        string='Parent Location',
    )
    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
    )

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" %
                   (self._table,
                    "select * from stock_location",))

    @api.model
    def _name_get(self, location):
        name = location.name
        while location.location_id and location.usage != 'view':
            location = location.location_id
            name = location.name + '/' + name
        return name

    @api.multi
    def name_get(self):
        res = []
        for location in self:
            res.append((location.id, self._name_get(location)))
        return res
