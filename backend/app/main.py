"""Production application assembled from the complete validated module catalog."""

from app.platform.application import create_application
from app.platform.modules.backend_catalog import registered_backend_modules

app = create_application(registered_backend_modules)
