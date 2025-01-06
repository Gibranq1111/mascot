from odoo import api, SUPERUSER_ID
import logging
import traceback

_logger = logging.getLogger(__name__)

def analyze_fields(cr, registry):
    """
    Función para analizar campos después de la instalación del módulo
    """
    try:
        _logger.info("Iniciando script de análisis")
        with api.Environment.manage():
            env = api.Environment(cr, SUPERUSER_ID, {})
            analyze_loyalty_models(env)
            _logger.info("Análisis completado exitosamente")
    except Exception as e:
        _logger.error(f"Error crítico durante el análisis de campos: {str(e)}")
        _logger.error(traceback.format_exc())

def analyze_loyalty_models(env):
    """Analiza los modelos relacionados con el programa de lealtad"""
    try:
        field_logger = env['field.logger'].sudo()
        
        # Lista de modelos a analizar
        models_to_analyze = [
            ('res.partner', 'Modelo base de contactos'),
            ('loyalty.program', 'Programa de lealtad'),
            ('loyalty.card', 'Tarjeta de lealtad'),
            ('loyalty.rule', 'Reglas de lealtad'),
            ('loyalty.reward', 'Recompensas de lealtad')
        ]
        
        for model_name, description in models_to_analyze:
            _logger.info(f"\n{'='*50}")
            _logger.info(f"Analizando modelo: {model_name}")
            _logger.info(f"Descripción: {description}")
            _logger.info(f"{'='*50}\n")
            
            try:
                model = env[model_name]
                
                # Obtener información básica del modelo
                _logger.info("\nInformación básica del modelo:")
                _logger.info(f"Nombre técnico: {model._name}")
                _logger.info(f"Descripción: {model._description}")
                
                # Obtener modelos heredados
                if hasattr(model, '_inherit'):
                    _logger.info("\nHereda de los modelos:")
                    inherits = model._inherit
                    if isinstance(inherits, str):
                        _logger.info(f"- {inherits}")
                    elif isinstance(inherits, (list, tuple)):
                        for inherit in inherits:
                            _logger.info(f"- {inherit}")
                
                # Obtener campos del modelo
                fields_data = model.fields_get()
                
                # Agrupar campos por tipo
                fields_by_type = {}
                for field_name, field_data in fields_data.items():
                    field_type = field_data.get('type')
                    if field_type not in fields_by_type:
                        fields_by_type[field_type] = []
                    
                    field_info = {
                        'name': field_name,
                        'string': field_data.get('string', 'Sin etiqueta'),
                        'required': field_data.get('required', False),
                        'readonly': field_data.get('readonly', False),
                        'store': field_data.get('store', True),
                        'relation': field_data.get('relation', False),
                    }
                    fields_by_type[field_type].append(field_info)
                
                # Registrar información por tipo de campo
                for field_type, fields in fields_by_type.items():
                    _logger.info(f"\nCampos de tipo {field_type}:")
                    _logger.info("----------------------------------------")
                    for field in fields:
                        field_desc = f"- {field['name']} ({field['string']})"
                        
                        attrs = []
                        if field['required']:
                            attrs.append("Required")
                        if field['readonly']:
                            attrs.append("Readonly")
                        if not field['store']:
                            attrs.append("Not Stored")
                        if field['relation']:
                            attrs.append(f"-> {field['relation']}")
                        
                        if attrs:
                            field_desc += f" [{' - '.join(attrs)}]"
                            
                        _logger.info(field_desc)
                
            except Exception as e:
                _logger.error(f"Error al analizar el modelo {model_name}: {str(e)}")
                _logger.error(traceback.format_exc())
                continue
        
        _logger.info("\nAnálisis completado")
        
    except Exception as e:
        _logger.error(f"Error crítico durante el análisis de modelos: {str(e)}")
        _logger.error(traceback.format_exc())

def get_model_dependencies(env, model_name):
    """
    Analiza las dependencias de un modelo.
    
    Args:
        env: Entorno de Odoo
        model_name: Nombre técnico del modelo a analizar
        
    Returns:
        dict: Diccionario con las dependencias encontradas
    """
    try:
        model = env[model_name]
        dependencies = {
            'inherited_models': [],
            'related_models': [],
            'dependent_fields': []
        }
        
        # Modelos heredados
        if hasattr(model, '_inherit'):
            inherits = model._inherit
            if isinstance(inherits, str):
                dependencies['inherited_models'].append(inherits)
            elif isinstance(inherits, (list, tuple)):
                dependencies['inherited_models'].extend(inherits)
        
        # Campos relacionales
        fields_data = model.fields_get()
        for field_name, field_data in fields_data.items():
            field_type = field_data.get('type')
            if field_type in ['many2one', 'one2many', 'many2many']:
                relation = field_data.get('relation')
                if relation:
                    dependencies['related_models'].append(relation)
                    dependencies['dependent_fields'].append({
                        'field_name': field_name,
                        'field_type': field_type,
                        'relation': relation
                    })
        
        return dependencies
        
    except Exception as e:
        _logger.error(f"Error al obtener dependencias del modelo {model_name}: {str(e)}")
        _logger.error(traceback.format_exc())
        return None

def validate_model_structure(env, model_name):
    """
    Valida la estructura de un modelo y sus dependencias.
    
    Args:
        env: Entorno de Odoo
        model_name: Nombre técnico del modelo a validar
        
    Returns:
        dict: Resultado de la validación
    """
    try:
        model = env[model_name]
        validation = {
            'model_exists': True,
            'table_exists': False,
            'missing_required_fields': [],
            'invalid_relations': [],
            'recommendations': []
        }
        
        # Verificar si la tabla existe en la base de datos
        cr = env.cr
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (model._table,))
        validation['table_exists'] = cr.fetchone()[0]
        
        # Verificar campos requeridos
        fields_data = model.fields_get()
        for field_name, field_data in fields_data.items():
            if field_data.get('required', False):
                try:
                    model._fields[field_name]
                except KeyError:
                    validation['missing_required_fields'].append(field_name)
        
        # Verificar relaciones
        for field_name, field_data in fields_data.items():
            if field_data.get('type') in ['many2one', 'one2many', 'many2many']:
                relation = field_data.get('relation')
                if relation and relation not in env:
                    validation['invalid_relations'].append({
                        'field': field_name,
                        'relation': relation
                    })
        
        # Generar recomendaciones
        if not validation['table_exists']:
            validation['recommendations'].append(
                "La tabla del modelo no existe en la base de datos. "
                "Ejecuta una actualización del módulo."
            )
            
        if validation['missing_required_fields']:
            validation['recommendations'].append(
                f"Hay campos requeridos faltantes: {', '.join(validation['missing_required_fields'])}. "
                "Verifica la definición del modelo."
            )
            
        if validation['invalid_relations']:
            validation['recommendations'].append(
                "Existen relaciones a modelos inexistentes. "
                "Verifica que los módulos relacionados estén instalados."
            )
            
        return validation
        
    except Exception as e:
        _logger.error(f"Error al validar estructura del modelo {model_name}: {str(e)}")
        _logger.error(traceback.format_exc())
        return None