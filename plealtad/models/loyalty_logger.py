from odoo import models, fields
import logging
import traceback
from datetime import datetime

_logger = logging.getLogger(__name__)

class LoyaltyLogger(models.Model):
   """
   Modelo centralizado para registro de eventos en el sistema de lealtad.
   Proporciona un mecanismo robusto de logging con información contextual.
   """
   _name = 'loyalty.logger'
   _description = 'Sistema Centralizado de Logging para Programa de Lealtad'
   _order = 'create_date desc'

   name = fields.Char(
       string='Título del Evento', 
       required=True,
       help='Resumen breve del evento registrado'
   )
   
   type = fields.Selection([
       ('register', 'Registro de Usuario'),
       ('login', 'Inicio de Sesión'),
       ('points', 'Gestión de Puntos'),
       ('reward', 'Gestión de Recompensas'),
       ('error', 'Error del Sistema'),
       ('warning', 'Advertencia'),
       ('info', 'Información General'),
   ], string='Categoría de Evento', required=True, default='info')
   
   level = fields.Selection([
       ('debug', 'Depuración'),
       ('info', 'Informativo'),
       ('warning', 'Advertencia'),
       ('error', 'Error'),
       ('critical', 'Crítico'),
   ], string='Nivel de Severidad', required=True, default='info')
   
   user_id = fields.Many2one('res.users', string='Usuario Relacionado')
   partner_id = fields.Many2one('res.partner', string='Cliente')
   
   details = fields.Text(
       string='Descripción Detallada',
       help='Información completa sobre el evento'
   )
   
   source_module = fields.Char(
       string='Módulo Origen', 
       help='Componente o módulo que generó el evento'
   )
   
   error_traceback = fields.Text(
       string='Traza de Error',
       help='Información técnica detallada del error'
   )
   
   timestamp = fields.Datetime(
       string='Hora del Evento', 
       default=fields.Datetime.now
   )

   def create_log(self, event_type, name, details=None, level='info', 
                  user=None, partner=None, source_module=None, error=None):
       """
       Método centralizado para crear registros de log.
       
       Args:
           event_type (str): Categoría del evento
           name (str): Título descriptivo
           details (str, optional): Descripción adicional
           level (str, optional): Nivel de severidad
           user (int, optional): ID del usuario relacionado
           partner (int, optional): ID del partner relacionado
           source_module (str, optional): Módulo que genera el log
           error (Exception, optional): Excepción capturada
       
       Returns:
           LoyaltyLogger: Registro de log creado
       """
       try:
           # Preparar información de error si existe
           traceback_info = None
           if error:
               traceback_info = ''.join(traceback.format_exception(
                   type(error), error, error.__traceback__
               ))
           
           # Crear registro de log
           log_values = {
               'name': name,
               'type': event_type,
               'level': level,
               'details': details or '',
               'user_id': user,
               'partner_id': partner,
               'source_module': source_module or 'loyalty_core',
               'error_traceback': traceback_info
           }
           
           log_record = self.create(log_values)
           
           # Log en consola para respaldo
           log_method = getattr(_logger, level, _logger.info)
           log_method(f"[{event_type.upper()}] {name} - {details or ''}")
           
           return log_record
       
       except Exception as e:
           _logger.error(f"Error al crear log: {e}")
           return False

   def log_event(self, event_type, name, level='info', details=None, 
                 user=None, partner=None, source=None, reference=None, **kwargs):
       """
       Método de logging compatible con implementaciones anteriores.
       
       Args:
           event_type (str): Tipo de evento
           name (str): Nombre del evento
           level (str, optional): Nivel de severidad
           details (str, optional): Detalles adicionales
           user (int, optional): ID de usuario
           partner (int, optional): ID de partner
           source (str, optional): Fuente del evento
           reference (str, optional): Referencia única
       
       Returns:
           LoyaltyLogger: Registro de log creado
       """
       return self.create_log(
           event_type=event_type,
           name=name,
           level=level,
           details=details,
           user=user,
           partner=partner,
           source_module=source,
           error=kwargs.get('error')
       )