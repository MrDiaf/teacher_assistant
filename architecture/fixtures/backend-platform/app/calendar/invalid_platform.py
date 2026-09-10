from app.platform.modules.backend_catalog import registered_backend_modules


def invalid_platform_import() -> object:
    return registered_backend_modules
