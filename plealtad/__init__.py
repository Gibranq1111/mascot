import logging

# Configuración global de logging
logging.getLogger('odoo.addons.plealtad').setLevel(logging.WARNING)

from . import models
from . import controllers
from . import tools