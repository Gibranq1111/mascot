import logging
from odoo import http, _, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import werkzeug

_logger = logging.getLogger(__name__)

class LoyaltyRegister(AuthSignupHome):
    """Controlador para el registro de usuarios en el programa de lealtad."""
    
    def _get_auth_signup_qcontext(self):
        """Extiende el contexto de registro base de Odoo."""
        qcontext = super(LoyaltyRegister, self)._get_auth_signup_qcontext()
        qcontext.update({
            'loyalty_program': True,
            'email_domains': ['gmail.com', 'outlook.com', 'hotmail.com', 'icloud.com'],
            'countries': request.env['res.country'].sudo().search([]),
        })
        return qcontext

    @http.route('/plealtad/verify/<string:token>', type='http', auth='public', website=True)
    def verify_token(self, token, **kw):
        """Ruta para verificación de token."""
        try:
            partner = request.env['res.partner'].sudo().search([
                ('verification_token', '=', token),
                ('verification_token_used', '=', False)
            ], limit=1)

            if not partner:
                return request.render('plealtad.verification_error', {
                    'error_message': 'Token inválido o ya utilizado.'
                })

            result = partner.verify_loyalty_token(token)
            
            if result['success']:
                # Enviar correo de bienvenida
                template = request.env.ref('plealtad.email_template_loyalty_welcome')
                template.sudo().send_mail(partner.id, force_send=True)
                
                return request.render('plealtad.verification_success', {
                    'message': result['message']
                })
            else:
                return request.render('plealtad.verification_error', {
                    'error_message': result['message']
                })

        except Exception as e:
            _logger.error(f'Error en verificación de token: {str(e)}')
            return request.render('plealtad.verification_error', {
                'error_message': 'Error en la verificación. Por favor, intente más tarde.'
            })

    @http.route('/plealtad/register', type='http', auth='public', website=True)
    def register_form(self, **kw):
        """Renderiza el formulario de registro del programa de lealtad."""
        _logger.info('Acceso al formulario de registro de lealtad')
        try:
            values = {
                'name': kw.get('name', ''),
                'email_prefix': kw.get('email_prefix', ''),
                'email_domain': kw.get('email_domain', ''),
                'phone': kw.get('phone', ''),
                'error': kw.get('error', ''),
                'has_error': bool(kw.get('error', '')),
                'email_domains': ['gmail.com', 'outlook.com', 'hotmail.com', 'icloud.com'],
                'countries': request.env['res.country'].sudo().search([]),
                'values': kw
            }
            
            if kw.get('country_id'):
                values['states'] = self._get_country_states(kw['country_id'])
                
            return request.render('plealtad.register_template', values)
        except Exception as e:
            _logger.error('Error al mostrar formulario de registro: %s', str(e))
            return request.redirect('/web/login')

    @http.route('/plealtad/register/submit', type='http', auth='public', website=True, methods=['POST'])
    def register_submit(self, **post):
        """Procesa el envío del formulario de registro."""
        logger = request.env['loyalty.logger'].sudo()
        try:
            # Validar datos del formulario
            self._validate_registration_data(post)
            
            # Preparar email
            email = f"{post.get('email_prefix')}@{post.get('email_domain')}"
            
            # Log de inicio de proceso
            logger.log_event(
                'register',
                'Inicio de proceso de registro',
                level='info',
                details=f"Intento de registro para email: {email}"
            )

            # Crear partner
            partner_values = {
                'name': post.get('name'),
                'email': email,
                'phone': post.get('phone'),
                'is_loyalty_registration': True
            }

            partner = request.env['res.partner'].sudo().create(partner_values)

            # Enviar correo de verificación
            template = request.env.ref('plealtad.email_template_loyalty_verification')
            template.sudo().with_context(base_url=request.env['ir.config_parameter'].sudo().get_param('web.base.url')).send_mail(partner.id, force_send=True)

            # Log de éxito
            logger.log_event(
                'register',
                'Registro exitoso',
                level='info',
                details=f'Usuario registrado exitosamente: {email}'
            )

            return request.render('plealtad.register_success_template', {
                'email': email
            })

        except ValidationError as e:
            return self._handle_registration_error(post, str(e))
        except Exception as e:
            _logger.error('Error en proceso de registro: %s', str(e))
            logger.log_event(
                'register',
                'Error en registro',
                level='error',
                details=str(e)
            )
            return self._handle_registration_error(
                post, 
                _('Ocurrió un error durante el registro. Por favor intente nuevamente.')
            )

    def _validate_registration_data(self, post):
        """Valida los datos del formulario de registro."""
        logger = request.env['loyalty.logger'].sudo()
        
        # Verificar campos requeridos
        required_fields = ['name', 'email_prefix', 'email_domain', 'phone', 
                         'password', 'confirm_password']
        for field in required_fields:
            if not post.get(field):
                logger.log_event(
                    'register',
                    'Error de validación',
                    level='warning',
                    details=f'Campo requerido faltante: {field}'
                )
                raise ValidationError(_('Todos los campos son obligatorios.'))
        
        # Validar contraseñas
        if post.get('password') != post.get('confirm_password'):
            logger.log_event(
                'register',
                'Error de validación',
                level='warning',
                details='Las contraseñas no coinciden'
            )
            raise ValidationError(_('Las contraseñas no coinciden.'))
        
        # Validar términos y condiciones
        if not post.get('terms_accepted'):
            logger.log_event(
                'register',
                'Error de validación',
                level='warning',
                details='Términos y condiciones no aceptados'
            )
            raise ValidationError(_('Debe aceptar los términos y condiciones.'))

        # Validar duplicados
        email = f"{post.get('email_prefix')}@{post.get('email_domain')}"
        if request.env['res.partner'].sudo().search_count([('email', '=', email)]):
            logger.log_event(
                'register',
                'Error de validación',
                level='warning',
                details=f'Email duplicado: {email}'
            )
            raise ValidationError(_('Este correo electrónico ya está registrado.'))

        phone = post.get('phone')
    def _validate_registration_data(self, post):
       """Valida los datos del formulario de registro.""" 
       logger = request.env['loyalty.logger'].sudo()

       # Validar duplicados de teléfono 
       phone = post.get('phone')
       if phone and request.env['res.partner'].sudo().search_count([('phone', '=', phone)]):
           logger.log_event(
               'register',
               'Error de validación',
               level='warning',
               details=f'Teléfono duplicado: {phone}'
           )
           raise ValidationError(_('Este número de teléfono ya está registrado.'))

    def _handle_registration_error(self, post, error_message):
       """Maneja los errores durante el registro y prepara la respuesta."""
       values = {
           'error': error_message,
           'email_domains': ['gmail.com', 'outlook.com', 'hotmail.com', 'icloud.com'],
           'values': post,
           'countries': request.env['res.country'].sudo().search([])
       }
       if post.get('country_id'):
           values['states'] = self._get_country_states(post['country_id'])
       return request.render('plealtad.register_template', values)

    def _get_country_states(self, country_id):
       """Obtiene los estados/provincias de un país."""
       if not country_id:
           return []
       return request.env['res.country.state'].sudo().search([
           ('country_id', '=', int(country_id))
       ])

    @http.route('/plealtad/get_states', type='json', auth='public')
    def get_states(self, country_id):
       """Endpoint JSON para obtener estados/provincias de un país."""
       if not country_id:
           return []
           
       states = self._get_country_states(country_id)
       return [{
           'id': state.id,
           'name': state.name
       } for state in states]

    @http.route('/plealtad/check_email', type='json', auth='public')
    def check_email(self, email):
       """Endpoint JSON para verificar disponibilidad de email."""
       exists = request.env['res.partner'].sudo().search_count([
           ('email', '=', email)
       ]) > 0
       
       return {
           'available': not exists,
           'message': _('Este email ya está registrado.') if exists else ''
       }

    @http.route('/plealtad/check_phone', type='json', auth='public')
    def check_phone(self, phone):
       """Endpoint JSON para verificar disponibilidad de teléfono."""
       exists = request.env['res.partner'].sudo().search_count([
           ('phone', '=', phone)
       ]) > 0
       
       return {
           'available': not exists,
           'message': _('Este teléfono ya está registrado.') if exists else ''
       }

    @http.route('/plealtad/resend_verification', type='json', auth='public')
    def resend_verification(self, email):
       """Endpoint para reenviar correo de verificación."""
       partner = request.env['res.partner'].sudo().search([
           ('email', '=', email),
           ('is_loyalty_active', '=', False),
           ('verification_token_used', '=', False)
       ], limit=1)

       if not partner:
           return {
               'success': False,
               'message': _('No se encontró un registro pendiente de verificación.')
           }

       # Generar nuevo token
       token, expiry = partner.generate_verification_token()
       partner.write({
           'verification_token': token,
           'verification_token_expiry': expiry
       })

       # Reenviar correo
       template = request.env.ref('plealtad.email_template_loyalty_verification')
       template.sudo().with_context(
           base_url=request.env['ir.config_parameter'].sudo().get_param('web.base.url')
       ).send_mail(partner.id, force_send=True)

       return {
           'success': True,
           'message': _('Se ha enviado un nuevo correo de verificación.')
       }

    # Métodos de soporte
    def _create_user_from_partner(self, partner, password):
       """Crea un usuario del portal para el partner."""
       # Generar nombre de usuario único basado en el email
       login = partner.email
       
       # Crear usuario
       user_values = {
           'login': login,
           'partner_id': partner.id,
           'password': password,
           'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])]
       }
       
       return request.env['res.users'].sudo().create(user_values)

    def _send_welcome_email(self, partner):
       """Envía el correo de bienvenida al programa de lealtad."""
       template = request.env.ref('plealtad.email_template_loyalty_welcome')
       template.sudo().with_context(
           base_url=request.env['ir.config_parameter'].sudo().get_param('web.base.url')
       ).send_mail(partner.id, force_send=True)