import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class LoyaltyLogin(Home):

    @http.route('/plealtad/login', type='http', auth='public', website=True)
    def loyalty_login(self, redirect=None, **kw):
        """Página de login personalizada para el programa de lealtad"""
        try:
            _logger.info('Acceso a la página de login del programa de lealtad')
            
            # Si el usuario ya está autenticado, redirigir al dashboard
            if request.session.uid:
                return request.redirect('/my/loyalty')

            values = {
                'error': None,
                'error_message': None,
                'redirect': redirect,
                # Añadir dominios de email para consistencia
                'email_domains': ['gmail.com', 'outlook.com', 'hotmail.com', 'icloud.com']
            }

            if request.httprequest.method == 'POST':
                _logger.info('Intento de login recibido')
                try:
                    values = self.try_loyalty_login(request.params)
                    if not values.get('error'):
                        return request.redirect(self._get_redirect_url(values.get('redirect')))
                except ValidationError as e:
                    values['error'] = _('Error de autenticación')
                    values['error_message'] = str(e)
                    _logger.warning(f'Error de autenticación: {str(e)}')
                except Exception as e:
                    values['error'] = _('Error del sistema')
                    values['error_message'] = _('Ocurrió un error inesperado. Por favor, intente más tarde.')
                    _logger.error(f'Error en el proceso de login: {str(e)}')

            return request.render('plealtad.plealtad_login', values)
            
        except Exception as e:
            _logger.error(f'Error al mostrar página de login: {str(e)}')
            return request.redirect('/web/login')

    def try_loyalty_login(self, params):
        """Intenta autenticar al usuario y verifica su estado en el programa de lealtad"""
        # Verificar que tengamos una base de datos válida
        if not request.session.db:
            raise ValidationError(_('No se pudo conectar a la base de datos.'))
        
        # Combinar prefijo y dominio de email si es necesario
        if 'email_prefix' in params and 'email_domain' in params:
            login = f"{params.get('email_prefix', '').strip()}@{params.get('email_domain', '').strip()}"
        else:
            login = params.get('login', '').strip()
        
        password = params.get('password', '').strip()
        
        if not login or not password:
            raise ValidationError(_('Por favor, ingrese su email y contraseña.'))
            
        _logger.info(f'Verificando credenciales para: {login}')
        
        # Intentar autenticación
        try:
            request.session.authenticate(request.session.db, login, password)
        except Exception as e:
            _logger.error(f'Error de autenticación: {str(e)}')
            raise ValidationError(_('Email o contraseña incorrectos.'))
            
        if not request.session.uid:
            raise ValidationError(_('Email o contraseña incorrectos.'))
            
        # Verificar estado en programa de lealtad
        user = request.env['res.users'].sudo().browse(request.session.uid)
        partner = user.partner_id

        # Verificar si el programa de lealtad está activo
        if not partner.is_loyalty_active:
            # Si no está activo, intentar activarlo
            try:
                partner.sudo().activate_loyalty_program()
                _logger.info(f'Programa de lealtad activado para usuario: {login}')
            except Exception as e:
                _logger.error(f'Error al activar programa de lealtad: {str(e)}')
                raise ValidationError(_('Error al activar el programa de lealtad.'))
                    
        return {
            'error': None,
            'redirect': '/my/loyalty'
        }

    def _get_redirect_url(self, redirect):
        """Obtiene la URL de redirección segura"""
        if not redirect:
            return '/my/loyalty'
            
        # Verificar que la redirección sea segura (dentro del mismo sitio)
        if not redirect.startswith('/') or '//' in redirect:
            return '/my/loyalty'
            
        return redirect