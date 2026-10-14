"""Contexto (datos) que usa el generador del proyecto."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ProjectContext:
    """Datos del proyecto a generar."""

    project_name: str  # Nombre legible, ej: "Mi Proyecto Back"
    slug: str  # Nombre para carpetas/paquetes, ej: mi_proyecto_back
    description: str = ""
    author: str = ""
    port: int = 8888
    db_name: str = ""  # Si vacío se usa slug
    include_celery: bool = True
    include_redis: bool = True
    pybernate_url: str = ""  # URL del repo pybernate_orm; vacío = usa la URL por defecto (siempre se enlaza)
    template: Literal["minimal", "full"] = "full"
    container_name_prefix: str = ""  # ej: xrrhh -> xrrhh_api, xrrhh_db
    user_class: str = "usuario"  # settings.USER_CLASS: clase CMS (ej. usuario, persona)
    user_login: str = "desc_usuario"  # settings.USER_LOGIN: atributo del modelo para el login (ej. desc_usuario)
    user_password: str = "password"  # settings.USER_PASSWORD: nombre del atributo de contraseña en el modelo

    def __post_init__(self) -> None:
        if not self.db_name:
            self.db_name = self.slug
        if not self.container_name_prefix:
            self.container_name_prefix = self.slug.replace("_", "")
