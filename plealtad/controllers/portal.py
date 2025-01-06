import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)

class LoyaltyPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        """Añade valores del programa de lealtad al layout del portal"""
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        try:
            _logger.info(f'Preparando valores de lealtad para partner: {partner.name}')
            
            # Determinamos qué campos usar basándonos en su disponibilidad
            loyalty_points = (
                getattr(partner, 'loy_points', None) or 
                getattr(partner, 'loyalty_points', 0)
            )
            
            is_active = (
                getattr(partner, 'loy_active', False) or 
                getattr(partner, 'is_loyalty_active', False)
            )
            
            values.update({
                'loyalty_points': loyalty_points,
                'is_loyalty_active': is_active,
                'loyalty_program': partner.loyalty_program_id,
                'page_name': 'loyalty'
            })
            
            _logger.info(f'Valores de lealtad preparados: Puntos={loyalty_points}, Activo={is_active}')
            
        except Exception as e:
            _logger.error(f'Error al preparar valores del portal: {str(e)}')
            values.update({
                'loyalty_points': 0,
                'is_loyalty_active': False,
                'loyalty_program': False,
                'page_name': 'loyalty'
            })
            
        return values

    @http.route(['/my/loyalty'], type='http', auth='user', website=True)
    def portal_loyalty(self, **kw):
        try:
            _logger.info('Acceso al dashboard de lealtad')
            values = self._prepare_portal_layout_values()
            
            partner = request.env.user.partner_id
            
            # Verificación más robusta del estado de lealtad
            is_active = (
                partner.is_loyalty_active or 
                (partner.loyalty_program_id and partner.loyalty_program_id.active)
            )
            
            _logger.info(f'Estado de lealtad para {partner.name}: {is_active}')
            
            # Si no está activo, activar automáticamente
            if not is_active:
                try:
                    partner.sudo().activate_loyalty_program()
                    is_active = True
                    _logger.info(f'Programa de lealtad activado automáticamente para {partner.name}')
                except Exception as e:
                    _logger.error(f'Error al activar programa de lealtad: {str(e)}')
            
            # Obtener información del programa de lealtad
            loyalty_card = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id)
            ], limit=1)
            
            # Valores específicos de lealtad
            values.update({
                'loyalty_card': loyalty_card,
                'loyalty_points': loyalty_card.points if loyalty_card else 0,
                'loyalty_program': partner.loyalty_program_id,
                'is_loyalty_active': is_active
            })
            
            if not is_active:
                _logger.warning(f'Usuario sin programa de lealtad activo: {partner.name}')
                return request.render('plealtad.loyalty_inactive', values)
                
            return request.render('plealtad.loyalty_dashboard', values)
            
        except Exception as e:
            _logger.error(f'Error al mostrar dashboard de lealtad: {str(e)}')
            # En lugar de redirigir al portal de Odoo, renderizamos nuestra plantilla de error
            return request.render('plealtad.loyalty_error', {
                'error_message': 'No se pudo acceder al dashboard de lealtad. Por favor, contacte con soporte.',
                'redirect_url': '/plealtad/login'
            })