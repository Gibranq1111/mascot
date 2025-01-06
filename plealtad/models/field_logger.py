from odoo import models, fields
import logging
import traceback

_logger = logging.getLogger(__name__)

class FieldLogger(models.Model):
    """
    Modelo para registro y análisis de estructuras de modelos.
    Permite un seguimiento detallado de la configuración de campos.
    """
    _name = 'field.logger'
    _description = 'Registro de Análisis de Estructura de Modelos'

    name = fields.Char(string='Modelo Analizado', required=True)
    log_date = fields.Datetime(string='Fecha de Análisis', default=fields.Datetime.now)
    log_content = fields.Text(string='Contenido del Análisis')
    log_type = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error')
    ], default='info')

    def log_model_structure(self, model_name, log_type='info'):
        """
        Registra la estructura detallada de un modelo.
        
        Args:
            model_name (str): Nombre técnico del modelo
            log_type (str, optional): Tipo de log
        
        Returns:
            FieldLogger: Registro de log creado
        """
        try:
            model = self.env[model_name]
            log_content = [f"Análisis Estructural: {model_name}"]
            
            # Información básica del modelo
            log_content.append(f"Descripción: {model._description}")
            
            # Campos del modelo
            fields_data = model.fields_get()
            log_content.append("\nEstructura de Campos:")
            
            for field_name, field_info in fields_data.items():
                field_details = (
                    f"- {field_name}: "
                    f"Tipo={field_info.get('type', 'N/A')} | "
                    f"Requerido={field_info.get('required', False)} | "
                    f"Solo Lectura={field_info.get('readonly', False)}"
                )
                log_content.append(field_details)
            
            log_record = self.create({
                'name': model_name,
                'log_content': '\n'.join(log_content),
                'log_type': log_type
            })
            
            return log_record
        
        except Exception as e:
            error_log = self.create({
                'name': model_name,
                'log_content': f"Error en análisis: {str(e)}",
                'log_type': 'error'
            })
            _logger.error(f"Error analizando {model_name}: {traceback.format_exc()}")
            return error_log