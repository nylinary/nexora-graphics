"""Deprecated: IService moved to app.application.interfaces.services.

Service interfaces reference application-layer Commands and therefore
cannot live in domain/. Use:

    from app.application.interfaces.services import IService
"""
