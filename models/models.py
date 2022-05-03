# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TankStage(models.Model):
    _name = 'petrol.tank.stage'
    _description = 'Petrol Tank Stage'

    name = fields.Char(string="Stage Name", required=True)


class PetrolTank(models.Model):
    _name = 'petrol.tank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Petrol Tank'

    name = fields.Char(required=True)
    capacity = fields.Float()
    used = fields.Float(compute='compute_used', store=True)
    charged = fields.Float(compute='compute_charged', store=True)
    balance = fields.Float(compute='compute_balance', store=True)
    balance_progress = fields.Float(compute='compute_balance')
    last_charge = fields.Date(compute='compute_last_charge', store=True)
    stage_id = fields.Many2one('petrol.tank.stage')
    charge_ids = fields.One2many('petrol.tank.charge', 'tank_id')
    use_ids = fields.One2many('petrol.tank.use', 'tank_id')
    first_charge_balance = fields.Float(compute='compute_first_charge_balance', store=True)

    @api.depends('capacity', 'used', 'charge_ids.quantity')
    def compute_first_charge_balance(self):
        for rec in self:
            if rec.capacity and rec.used and rec.charge_ids:
                first_charge = sum([rec.quantity for rec in rec.charge_ids[0]])
                rec.first_charge_balance = rec.capacity + rec.used - first_charge
            else:
                rec.first_charge_balance = 0

    @api.depends('use_ids.quantity')
    def compute_used(self):
        for rec in self:
            rec.used = 0
            if rec.use_ids:
                rec.used = sum([rec.quantity for rec in rec.use_ids])

    @api.depends('charge_ids.quantity')
    def compute_charged(self):
        for rec in self:
            rec.charged = 0
            if rec.charge_ids:
                rec.charged = sum([rec.quantity for rec in rec.charge_ids])

    @api.depends('capacity', 'used', 'charged')
    def compute_balance(self):
        for rec in self:
            rec.balance = rec.charged + rec.capacity - rec.used
            if rec.capacity:
                rec.balance_progress = rec.balance * 100 / rec.capacity
            else:
                rec.balance_progress = 0

    @api.depends('charge_ids.charge_date')
    def compute_last_charge(self):
        for rec in self:
            if rec.charge_ids:
                dates = []
                for charge in rec.charge_ids:
                    if charge.charge_date:
                        dates.append(charge.charge_date)
                if dates:
                    rec.last_charge = max(dates)
            else:
                rec.last_charge = False


class TankCharge(models.Model):
    _name = 'petrol.tank.charge'
    _description = 'Petrol Tank Charge'

    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    tank_id = fields.Many2one('petrol.tank')
    charge_date = fields.Date()
    quantity = fields.Float()
    cost = fields.Float()

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            tank = self.env['petrol.tank'].browse(vals.get('tank_id'))
            if tank:
                vals['name'] = tank.name + ' ' + self.env['ir.sequence'].next_by_code('petrol.tank.charge') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('petrol.tank.charge') or _('New')
        res = super(TankCharge, self).create(vals)
        return res


class TankUse(models.Model):
    _name = 'petrol.tank.use'
    _description = 'Petrol Tank Use'

    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    tank_id = fields.Many2one('petrol.tank', string="Source of Record")
    vehicle_id = fields.Many2one('fleet.vehicle')
    odometer = fields.Many2one('fleet.vehicle.odometer')
    odometer_value = fields.Float(string="Current Odometer")
    current_quantity = fields.Float()
    quantity = fields.Float()
    use_quantity = fields.Float(compute='compute_use_quantity', store=True)
    datetime = fields.Datetime(string="Date & Time")
    last_odometer = fields.Float(compute='compute_last_odometer', store=True)
    last_quantity = fields.Float(compute='compute_last_odometer', store=True)
    liter_per_km_rate = fields.Float(compute='compute_liter_per_km_rate', store=True)
    used_odometer = fields.Float(compute='compute_used_odometer', store=True)
    used_quantity = fields.Float(compute='compute_used_quantity', store=True)

    @api.depends('odometer_value', 'last_odometer')
    def compute_used_odometer(self):
        for rec in self:
            rec.used_odometer = rec.odometer_value - rec.last_odometer

    @api.depends('current_quantity', 'last_quantity')
    def compute_used_quantity(self):
        for rec in self:
            if (rec.current_quantity and rec.last_quantity) and (rec.current_quantity > rec.last_quantity):
                rec.used_quantity = rec.current_quantity - rec.last_quantity
            else:
                rec.used_quantity = 0

    @api.depends('current_quantity', 'quantity')
    def compute_use_quantity(self):
        for rec in self:
            rec.use_quantity = rec.quantity + rec.current_quantity

    @api.depends('vehicle_id')
    def compute_last_odometer(self):
        for rec in self:
            if rec.vehicle_id:
                last_odometers = self.env['fleet.vehicle.odometer'].search([
                    ('vehicle_id', '=', rec.vehicle_id.id), ('use_id', '!=', False),
                    ('create_date', '<', rec.create_date),
                ])
                if last_odometers:
                    last_odometers.mapped('date')
                    rec.last_odometer = last_odometers[-1].value
                    rec.last_quantity = last_odometers[-1].use_id.use_quantity

    @api.depends('odometer_value', 'last_odometer', 'current_quantity', 'last_quantity')
    def compute_liter_per_km_rate(self):
        for rec in self:
            if rec.odometer_value and rec.last_odometer and rec.current_quantity and rec.last_quantity:
                if rec.last_quantity - rec.quantity != 0:
                    rec.liter_per_km_rate = round((rec.odometer_value - rec.last_odometer) / (rec.last_quantity - rec.current_quantity), 2)
                else:
                    rec.liter_per_km_rate = 0

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vehicle = self.env['fleet.vehicle'].browse(vals.get('vehicle_id'))
            vals['name'] = vehicle.name + ' ' + self.env['ir.sequence'].next_by_code('petrol.tank.use') or _('New')
        res = super(TankUse, self).create(vals)
        if vals.get('vehicle_id', False) and vals.get('datetime', False) and vals.get('odometer_value', False):
            new_odometer = self.env['fleet.vehicle.odometer'].create({
                'vehicle_id': res.vehicle_id.id,
                'date': res.datetime,
                'use_id': res.id,
                'value': res.odometer_value,
            })
            res.odometer = new_odometer.id
        return res


class Odometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'

    use_id = fields.Many2one('petrol.tank.use')