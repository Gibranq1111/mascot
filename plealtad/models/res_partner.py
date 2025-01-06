import logging
import random
import string
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # =========================================================================
    # Campos base de lealtad y verificación
    # =========================================================================
    loyalty_card_ids = fields.One2many(
        'loyalty.card',
        'partner_id',
        string='Tarjetas de Lealtad',
        help='Tarjetas de lealtad asociadas al cliente'
    )

    loyalty_program_id = fields.Many2one(
        'loyalty.program',
        string='Programa de Lealtad',
        compute='_compute_loyalty_program',
        store=True,
        help='Programa de lealtad actual del cliente'
    )

    points = fields.Float(
        string='Puntos del Programa',
        compute='_compute_loyalty_points',
        store=True,
        help='Puntos acumulados en el programa de lealtad'
    )
    
    is_loyalty_active = fields.Boolean(
        string='Programa Activo',
        compute='_compute_loyalty_active',
        store=True,
        help='Indica si el cliente tiene un programa de lealtad activo'
    )

    is_loyalty_registration = fields.Boolean(
        string='Registro de Lealtad',
        help='Indica si el registro es para el programa de lealtad',
        default=False,
        copy=False
    )

    # Campos para tracking de puntos y recompensas
    last_points_update = fields.Datetime(
        string='Última Actualización de Puntos',
        help='Fecha y hora de la última actualización de puntos'
    )

    points_expiration_date = fields.Date(
        string='Fecha de Expiración de Puntos',
        compute='_compute_points_expiration',
        store=True,
        help='Fecha en que expirarán los puntos actuales'
    )

    total_points_earned = fields.Float(
        string='Total de Puntos Ganados',
        compute='_compute_total_points',
        help='Total histórico de puntos ganados'
    )

    total_points_redeemed = fields.Float(
        string='Total de Puntos Redimidos',
        compute='_compute_total_points',
        help='Total histórico de puntos redimidos'
    )

    first_purchase_made = fields.Boolean(
        string='Primera Compra Realizada',
        default=False,
        help='Indica si el cliente ya realizó su primera compra con descuento'
    )

    loyalty_history_ids = fields.One2many(
        'loyalty.history',
        'partner_id',
        string='Historial de Lealtad',
        help='Historial de transacciones de lealtad'
    )

    # =========================================================================
    # Campos computados y sus dependencias
    # =========================================================================
    @api.depends('loyalty_card_ids', 'loyalty_card_ids.points')
    def _compute_loyalty_points(self):
        """Calcula los puntos actuales del programa de lealtad"""
        for partner in self:
            try:
                active_cards = partner.loyalty_card_ids.filtered(
                    lambda c: c.program_id.program_type == 'loyalty' and 
                             c.program_id.active
                )
                partner.points = sum(active_cards.mapped('points'))
                partner.last_points_update = fields.Datetime.now()
                _logger.info(f'Puntos calculados para {partner.name}: {partner.points}')
            except Exception as e:
                _logger.error(f'Error al calcular puntos para {partner.name}: {str(e)}')
                partner.points = 0.0

    @api.depends('loyalty_card_ids.program_id')
    def _compute_loyalty_active(self):
        """Determina si el partner tiene un programa de lealtad activo"""
        for partner in self:
            try:
                active_cards = partner.loyalty_card_ids.filtered(
                    lambda c: c.program_id.program_type == 'loyalty' and 
                             c.program_id.active
                )
                partner.is_loyalty_active = bool(active_cards)
                _logger.info(f'Estado de lealtad para {partner.name}: {partner.is_loyalty_active}')
            except Exception as e:
                _logger.error(f'Error al verificar estado de lealtad para {partner.name}: {str(e)}')
                partner.is_loyalty_active = False

    @api.depends('loyalty_card_ids.program_id')
    def _compute_loyalty_program(self):
        """Obtiene el programa de lealtad activo del partner"""
        for partner in self:
            try:
                active_card = partner.loyalty_card_ids.filtered(
                    lambda c: c.program_id.program_type == 'loyalty' and 
                             c.program_id.active
                )
                partner.loyalty_program_id = active_card[0].program_id if active_card else False
                _logger.info(f'Programa obtenido para {partner.name}: {partner.loyalty_program_id.name if partner.loyalty_program_id else "Ninguno"}')
            except Exception as e:
                _logger.error(f'Error al obtener programa de lealtad para {partner.name}: {str(e)}')
                partner.loyalty_program_id = False

    @api.depends('last_points_update')
    def _compute_points_expiration(self):
        """Calcula la fecha de expiración de los puntos"""
        expiration_days = 365  # 1 año de vigencia
        for partner in self:
            try:
                if partner.last_points_update:
                    partner.points_expiration_date = fields.Date.from_string(partner.last_points_update) + timedelta(days=expiration_days)
                else:
                    partner.points_expiration_date = False
                _logger.info(f'Fecha de expiración calculada para {partner.name}: {partner.points_expiration_date}')
            except Exception as e:
                _logger.error(f'Error al calcular fecha de expiración para {partner.name}: {str(e)}')
                partner.points_expiration_date = False

    @api.depends('loyalty_history_ids')
    def _compute_total_points(self):
        """Calcula el total histórico de puntos ganados y redimidos"""
        for partner in self:
            try:
                earned = sum(partner.loyalty_history_ids.filtered(lambda h: h.transaction_type == 'earn').mapped('points'))
                redeemed = sum(partner.loyalty_history_ids.filtered(lambda h: h.transaction_type == 'redeem').mapped('points'))
                
                partner.total_points_earned = earned
                partner.total_points_redeemed = redeemed
                
                _logger.info(f'Totales calculados para {partner.name}: Ganados={earned}, Redimidos={redeemed}')
            except Exception as e:
                _logger.error(f'Error al calcular totales para {partner.name}: {str(e)}')
                partner.total_points_earned = 0.0
                partner.total_points_redeemed = 0.0

    # =========================================================================
    # Métodos de manejo de puntos y recompensas
    # =========================================================================
    def add_loyalty_points(self, points, reason=None, order_reference=None):
        """Añade puntos al programa de lealtad del partner"""
        self.ensure_one()
        try:
            if not self.is_loyalty_active:
                raise ValidationError(_('El cliente no tiene un programa de lealtad activo.'))
                
            active_card = self.loyalty_card_ids.filtered(
                lambda c: c.program_id.program_type == 'loyalty' and 
                         c.program_id.active
            )
            
            if not active_card:
                raise ValidationError(_('No se encontró una tarjeta de lealtad activa.'))
                
            active_card[0].write({
                'points': active_card[0].points + points,
            })

            # Registrar la transacción en el historial
            self.env['loyalty.history'].create({
                'partner_id': self.id,
                'card_id': active_card[0].id,
                'points': points,
                'transaction_type': 'earn',
                'reason': reason or _('Puntos añadidos por compra'),
                'order_reference': order_reference,
                'date': fields.Datetime.now()
            })
            
            _logger.info(f'Puntos añadidos para {self.name}: {points}')
            return True
            
        except Exception as e:
            _logger.error(f'Error al añadir puntos: {str(e)}')
            raise ValidationError(_('Error al añadir puntos de lealtad.'))

    def redeem_points(self, points_to_redeem, order_reference=None):
        """Redime puntos del programa de lealtad"""
        self.ensure_one()
        try:
            if not self.is_loyalty_active:
                raise ValidationError(_('El cliente no tiene un programa de lealtad activo.'))

            if points_to_redeem > self.points:
                raise ValidationError(_('Puntos insuficientes para redención.'))

            active_card = self.loyalty_card_ids.filtered(
                lambda c: c.program_id.program_type == 'loyalty' and 
                         c.program_id.active
            )

            if not active_card:
                raise ValidationError(_('No se encontró una tarjeta de lealtad activa.'))

            # Registrar la redención
            self.env['loyalty.history'].create({
                'partner_id': self.id,
                'card_id': active_card[0].id,
                'points': points_to_redeem,
                'transaction_type': 'redeem',
                'reason': _('Redención de puntos'),
                'order_reference': order_reference,
                'date': fields.Datetime.now()
            })

            # Actualizar puntos
            active_card[0].write({
                'points': active_card[0].points - points_to_redeem
            })

            # Enviar correo de confirmación
            self._send_redemption_email(points_to_redeem, order_reference)

            _logger.info(f'Puntos redimidos para {self.name}: {points_to_redeem}')
            return True

        except Exception as e:
            _logger.error(f'Error al redimir puntos: {str(e)}')
            raise ValidationError(_('Error al redimir puntos de lealtad.'))

    def _send_redemption_email(self, points_redeemed, order_reference):
        """Envía correo de confirmación de redención"""
        try:
            template = self.env.ref('plealtad.email_template_points_redemption')
            template.with_context(
                points_before=self.points + points_redeemed,
                points_redeemed=points_redeemed,
                points_after=self.points,
                order_reference=order_reference
            ).send_mail(self.id, force_send=True)
            
            _logger.info(f'Correo de redención enviado a {self.name}')
        except Exception as e:
            _logger.error(f'Error al enviar correo de redención: {str(e)}')

    # =========================================================================
    # Validaciones
    # =========================================================================
    @api.constrains('email')
    def _check_unique_email(self):
        """Valida que el email sea único"""
        for partner in self:
            if partner.email:
                _logger.info(f'Validando unicidad de email: {partner.email}')
                duplicate = self.search([
                    ('email', '=ilike', partner.email),
                    ('id', '!=', partner.id)
                ])
                if duplicate:
                    _logger.warning(f'Email duplicado encontrado: {partner.email}')
                    raise ValidationError(_('Este correo electrónico ya está registrado.'))

    @api.constrains('phone')
    def _check_unique_phone(self):
        """Valida que el teléfono sea único"""
        for partner in self:
            if partner.phone:
                _logger.info(f'Validando unicidad de teléfono: {partner.phone}')
                normalized_phone = ''.join(filter(str.isdigit, partner.phone))
                duplicate = self.search([
                    ('phone', '!=', False),
                    ('id', '!=', partner.id)
                ]).filtered(lambda p: ''.join(filter(str.isdigit, p.phone)) == normalized_phone)
                
                if duplicate:
                    _logger.warning(f'Teléfono duplicado encontrado: {partner.phone}')
                    raise ValidationError(_('Este número de teléfono ya está registrado.'))

        # =========================================================================
        # Métodos de manejo de transacciones
        # =========================================================================
    def process_first_purchase_discount(self, order):
        """Procesa el descuento de primera compra"""
        self.ensure_one()
        try:
            if not self.is_loyalty_active:
                return False

            if self.first_purchase_made:
                return False

            # Aplicar descuento del 10%
            discount_amount = order.amount_total * 0.10
            order.write({
                'amount_total': order.amount_total - discount_amount
            })

            # Marcar primera compra como realizada
            self.write({
                'first_purchase_made': True
            })

            # Registrar en historial
            self.env['loyalty.history'].create({
                'partner_id': self.id,
                'transaction_type': 'discount',
                'points': 0,
                'amount': discount_amount,
                'reason': _('Descuento de primera compra (10%)'),
                'order_reference': order.name,
                'date': fields.Datetime.now()
            })

            _logger.info(f'Descuento de primera compra aplicado para {self.name}')
            return True

        except Exception as e:
            _logger.error(f'Error al procesar descuento de primera compra: {str(e)}')
            return False

    def process_purchase_points(self, order):
        """Procesa los puntos por compra"""
        self.ensure_one()
        try:
            if not self.is_loyalty_active:
                return False

            # Calcular puntos (5 puntos por peso)
            points_earned = float_round(order.amount_total * 5, precision_digits=2)

            # Añadir puntos
            self.add_loyalty_points(
                points_earned,
                _('Puntos por compra'),
                order.name
            )

            _logger.info(f'Puntos por compra procesados para {self.name}: {points_earned}')
            return True

        except Exception as e:
            _logger.error(f'Error al procesar puntos por compra: {str(e)}')
            return False

    def get_points_summary(self):
        """Obtiene resumen de puntos del cliente"""
        self.ensure_one()
        return {
            'points_available': self.points,
            'points_earned': self.total_points_earned,
            'points_redeemed': self.total_points_redeemed,
            'expiration_date': self.points_expiration_date,
            'is_active': self.is_loyalty_active,
            'first_purchase_available': not self.first_purchase_made
        }

    # =========================================================================
    # Métodos de utilidad
    # =========================================================================
    def check_points_expiration(self):
        """Verifica y procesa puntos expirados"""
        expired_partners = self.search([
            ('points_expiration_date', '<', fields.Date.today()),
            ('points', '>', 0)
        ])

        for partner in expired_partners:
            try:
                expired_points = partner.points
                
                # Registrar expiración en historial
                self.env['loyalty.history'].create({
                    'partner_id': partner.id,
                    'transaction_type': 'expire',
                    'points': expired_points,
                    'reason': _('Puntos expirados'),
                    'date': fields.Datetime.now()
                })

                # Actualizar puntos
                active_card = partner.loyalty_card_ids.filtered(
                    lambda c: c.program_id.program_type == 'loyalty' and 
                                c.program_id.active
                )
                if active_card:
                    active_card[0].write({'points': 0})

                _logger.info(f'Puntos expirados procesados para {partner.name}: {expired_points}')

            except Exception as e:
                _logger.error(f'Error al procesar expiración de puntos para {partner.name}: {str(e)}')
                continue

    @api.model
    def _cron_check_points_expiration(self):
        """Método para cron de verificación de puntos expirados"""
        try:
            self.check_points_expiration()
            _logger.info('Cron de verificación de puntos expirados ejecutado exitosamente')
        except Exception as e:
            _logger.error(f'Error en cron de verificación de puntos expirados: {str(e)}')

    def get_transaction_history(self, limit=None):
        """Obtiene el historial de transacciones del cliente"""
        self.ensure_one()
        domain = [('partner_id', '=', self.id)]
        
        if limit:
            return self.env['loyalty.history'].search(domain, limit=limit, order='date desc')
        return self.env['loyalty.history'].search(domain, order='date desc')