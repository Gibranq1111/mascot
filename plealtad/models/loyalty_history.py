# loyalty_history.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = 'Historial de Programa de Lealtad'
    _order = 'date desc'

    # Campos básicos
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        index=True,
        ondelete='cascade'
    )

    card_id = fields.Many2one(
        'loyalty.card',
        string='Tarjeta de Lealtad',
        required=True,
        ondelete='cascade'
    )

    date = fields.Datetime(
        string='Fecha',
        required=True,
        default=fields.Datetime.now,
        index=True
    )

    points = fields.Float(
        string='Puntos',
        required=True,
        help='Cantidad de puntos de la transacción'
    )

    transaction_type = fields.Selection([
        ('earn', 'Puntos Ganados'),
        ('redeem', 'Puntos Redimidos'),
        ('expire', 'Puntos Expirados'),
        ('discount', 'Descuento Aplicado')
    ], string='Tipo de Transacción', required=True)

    amount = fields.Float(
        string='Monto',
        help='Monto en dinero relacionado con la transacción'
    )

    order_reference = fields.Char(
        string='Referencia de Orden',
        help='Número de orden o ticket relacionado'
    )

    reason = fields.Char(
        string='Motivo',
        help='Descripción o motivo de la transacción'
    )

    # Campos computados
    points_balance = fields.Float(
        string='Balance de Puntos',
        compute='_compute_points_balance',
        store=True,
        help='Balance de puntos después de la transacción'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    # Métodos computados
    @api.depends('partner_id', 'date', 'points', 'transaction_type')
    def _compute_points_balance(self):
        """Calcula el balance de puntos después de cada transacción"""
        for record in self:
            try:
                # Obtener transacciones anteriores
                previous_transactions = self.search([
                    ('partner_id', '=', record.partner_id.id),
                    ('date', '<=', record.date),
                    ('id', '!=', record.id)
                ], order='date desc')

                balance = 0
                for trans in previous_transactions:
                    if trans.transaction_type == 'earn':
                        balance += trans.points
                    elif trans.transaction_type in ['redeem', 'expire']:
                        balance -= trans.points

                # Agregar transacción actual
                if record.transaction_type == 'earn':
                    balance += record.points
                elif record.transaction_type in ['redeem', 'expire']:
                    balance -= record.points

                record.points_balance = balance

            except Exception as e:
                _logger.error(f'Error al calcular balance de puntos: {str(e)}')
                record.points_balance = 0

    # Validaciones
    @api.constrains('points')
    def _check_points(self):
        """Validar que los puntos sean positivos"""
        for record in self:
            if record.points <= 0:
                raise ValidationError(_('Los puntos deben ser un valor positivo.'))

    @api.constrains('partner_id', 'card_id')
    def _check_card_partner(self):
        """Validar que la tarjeta pertenezca al cliente"""
        for record in self:
            if record.card_id.partner_id != record.partner_id:
                raise ValidationError(_('La tarjeta de lealtad no pertenece al cliente seleccionado.'))

    # Métodos del modelo
    def name_get(self):
        """Personalizar la visualización del registro"""
        result = []
        for record in self:
            name = f"{record.partner_id.name} - {dict(record._fields['transaction_type'].selection).get(record.transaction_type)}"
            if record.order_reference:
                name += f" ({record.order_reference})"
            result.append((record.id, name))
        return result

    @api.model
    def get_partner_balance(self, partner_id, date=None):
        """Obtiene el balance de puntos de un cliente en una fecha específica"""
        domain = [('partner_id', '=', partner_id)]
        if date:
            domain.append(('date', '<=', date))

        transactions = self.search(domain)
        balance = 0
        for trans in transactions:
            if trans.transaction_type == 'earn':
                balance += trans.points
            elif trans.transaction_type in ['redeem', 'expire']:
                balance -= trans.points
        return balance

    def export_history(self, partner_id, date_from=None, date_to=None):
        """Exporta el historial de transacciones de un cliente"""
        domain = [('partner_id', '=', partner_id)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        transactions = self.search(domain, order='date desc')
        return [{
            'fecha': t.date,
            'tipo': dict(t._fields['transaction_type'].selection).get(t.transaction_type),
            'puntos': t.points,
            'motivo': t.reason,
            'referencia': t.order_reference,
            'balance': t.points_balance
        } for t in transactions]