# -*- coding: utf-8 -*-
"""Plantillas de archivos para el proyecto backend."""

from .context import ProjectContext


def pyproject_toml(ctx: ProjectContext) -> str:
    deps = [
        'python = ">=3.12,<4.0"',
        'fastapi = ">=0.116.1,<0.117.0"',
        'uvicorn = ">=0.35.0,<0.36.0"',
        'psycopg2-binary = ">=2.9.10,<3.0.0"',
        'pydantic-settings = ">=2.10.1,<3.0.0"',
        'pydantic = "^2.11.9"',
        'python-dotenv = "^1.0.0"',
    ]
    if ctx.include_redis:
        deps.append('redis = ">=5.0.0,<6.0.0"')
        deps.append('fastapi-cache2 = "^0.2.2"')
    if ctx.include_celery:
        deps.extend([
            'celery = ">=5.3.0,<6.0.0"',
            'jinja2 = ">=3.1.0,<4.0.0"',
        ])
    deps.append('PyJWT = "^2.0.0"')

    dev_deps = (
        'black = "^24.0.0"\n'
        'pre-commit = "^3.0.0"\n'
        'commitizen = "^3.0.0"'
    )
    deps_str = "\n".join(deps)
    return f'''[tool.poetry]
name = "{ctx.slug}"
version = "0.1.0"
description = "{ctx.description or ""}"
authors = ["{ctx.author}"]
readme = "README.md"
package-mode = false

[tool.poetry.dependencies]
{deps_str}

[tool.poetry.group.dev.dependencies]
{dev_deps}

[tool.black]
line-length = 88
target-version = ['py312']
include = '\\.pyi?$'

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
'''


def run_py(ctx: ProjectContext) -> str:
    cors = ""
    if ctx.include_redis:
        cors = """
# User Context Middleware — por defecto DESACTIVADO (comentado).
# Descomenta tras el reverse engineering cuando exista el módulo ORM
# orm.common_services.<schema>.cms_<USER_CLASS> (settings.USER_CLASS en config.py).
# Si lo activas antes, el arranque puede fallar (p. ej. ModuleNotFoundError: cms_persona).
# from middlewares.user_context import UserContextMiddleware
# app.add_middleware(UserContextMiddleware)
"""
    return f'''import sys
from pathlib import Path

# Asegurar que la raíz del proyecto está en el path (para pybernate_orm)
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from app.api.main import api_router
from settings.config import settings

load_dotenv()


def custom_generate_unique_id(route: APIRoute) -> str:
    if not route.tags:
        return f"{{route.name}}"
    return f"{{route.tags[0]}}-{{route.name}}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    generate_unique_id_function=custom_generate_unique_id,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
{cors}

@app.get("/")
async def root():
    return {{"message": "Hello World", "project": "{ctx.project_name}"}}

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port={ctx.port}, reload=True)
'''


def settings_config(ctx: ProjectContext) -> str:
    uc = repr(ctx.user_class)
    ul = repr(ctx.user_login)
    up = repr(ctx.user_password)
    redis_block = (
        """
    REDIS_URL: str = "redis://redis:6379/0"
"""
        if ctx.include_redis
        else ""
    )
    return f'''import logging
from pathlib import Path
from typing import Annotated, Any
from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (funciona aunque el cwd sea otro)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("uvicorn.info")


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DOMAIN: str = "localhost"
    ENVIRONMENT: str = "dev"
    TIMEZONE: str = "America/Santiago"
    PROJECT_NAME: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "{ctx.db_name}"
    BACKEND_CORS_ORIGINS: Annotated[list | str, BeforeValidator(parse_cors)] = []
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str
    FIRST_SUPERUSER_NAME: str
    STORAGE_BACKEND: str = "local"{redis_block}
    USER_CLASS: str = {uc}
    USER_LOGIN: str = {ul}
    USER_PASSWORD: str = {up}
    USER_FILTERS: list = ["cod_empresa"]

settings = Settings()  # type: ignore
'''


def requirements_txt(ctx: ProjectContext) -> str:
    """requirements.txt para pip (fallback si no se usa poetry)."""
    lines = [
        "fastapi>=0.116.1",
        "uvicorn>=0.35.0",
        "psycopg2-binary>=2.9.10",
        "pydantic-settings>=2.10.1",
        "pydantic>=2.11.9",
        "python-dotenv>=1.0.0",
        "PyJWT>=2.0.0",
    ]
    if ctx.include_redis:
        lines.extend(["redis>=5.0.0", "fastapi-cache2>=0.2.2"])
    if ctx.include_celery:
        lines.extend(["celery>=5.3.0", "jinja2>=3.1.0"])
    return "\n".join(lines) + "\n"


def env_example(ctx: ProjectContext) -> str:
    redis_block = ""
    if ctx.include_redis:
        redis_block = """
REDIS_URL=redis://redis:6379/0
"""
    return f'''# Proyecto: {ctx.project_name}
PROJECT_NAME={ctx.project_name}
SECRET_KEY=changethis-generate-a-secure-key

POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB={ctx.db_name}
{redis_block}
USER_CLASS={ctx.user_class}
USER_LOGIN={ctx.user_login}
USER_PASSWORD={ctx.user_password}
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=admin123
FIRST_SUPERUSER_NAME=Admin
'''


def app_init(ctx: ProjectContext) -> str:
    if ctx.include_celery and ctx.include_redis:
        return '''from app.celery_app import celery_app as celery
from app.redis_client import redis_client

__all__ = ["celery", "redis_client"]
'''
    return '''__all__ = []
'''


def app_db_database(ctx: ProjectContext) -> str:
    return f'''from psycopg2 import connect as pg_connect
from psycopg2.extras import RealDictCursor
from settings.config import settings


class DatabaseEngine:
    _instances = {{}}

    def __new__(cls, base: str = "{ctx.db_name}"):
        if base not in cls._instances:
            instance = super(DatabaseEngine, cls).__new__(cls)
            settings.POSTGRES_DB = base
            instance.engine = pg_connect(
                "host=%s port=%s dbname=%s user=%s password=%s"
                % (
                    settings.POSTGRES_SERVER,
                    settings.POSTGRES_PORT,
                    settings.POSTGRES_DB,
                    settings.POSTGRES_USER,
                    settings.POSTGRES_PASSWORD,
                ),
                cursor_factory=RealDictCursor,
            )
            instance.engine.autocommit = True
            cls._instances[base] = instance
        return cls._instances[base]

    @classmethod
    def get_engine(cls, base: str = "{ctx.db_name}"):
        return cls._instances[base].engine


def get_db(base: str = "{ctx.db_name}"):
    engine = DatabaseEngine(base).get_engine(base)
    return engine
'''


def app_api_main(ctx: ProjectContext) -> str:
    return '''from fastapi import APIRouter
#from app.api.routes import auth, generic_master, generic_md, selects, menus, files

api_router = APIRouter()

# Rutas deshabilitadas por defecto: descomenta las que vayas a usar (ver README).
# api_router.include_router(router=auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(router=generic_master.router, prefix="/gm", tags=["Generic Master"])
# api_router.include_router(router=generic_md.router, prefix="/gmd", tags=["Generic Master-Detail"])
# api_router.include_router(router=selects.router, prefix="/selects", tags=["Selects"])
# api_router.include_router(router=menus.router, prefix="", tags=["Menus"])
# api_router.include_router(router=files.router, prefix="/api/files", tags=["Files"])
'''


def app_api_deps_full(ctx: ProjectContext) -> str:
    return f'''from typing import Annotated
from pydantic import BaseModel
from pybernate_orm.cache import get_cms_class
from utils.json_web_token import get_current_user
from fastapi import Depends, Request
from settings.config import settings

__UserModel = get_cms_class(settings.USER_CLASS).model


class UserDep(__UserModel):
    cod_empresa: int | None = None


class _Pagination(BaseModel):
    total: int | None = 0
    current: int | None = 1
    page_size: int | None = 10
    field: str | None = None
    order: str | None = "desc"
    cod_empresa: int | None = None
    search: str | None = ""
    filters: dict | None = {{}}


async def pagination_dependency(request: Request) -> _Pagination:
    q = dict(request.query_params)
    filters_ = [{{k.replace("filters[", "").replace("][", ",").replace("]", ""): v}} for k, v in request.query_params.items() if k.startswith("filters[")]
    filters = {{}}
    for item in filters_:
        for k, v in item.items():
            dato = k.split(",")
            if dato[0] not in filters:
                filters[dato[0]] = {{}}
            if filters[dato[0]].get(dato[1]) and isinstance(filters[dato[0]][dato[1]], list):
                filters[dato[0]][dato[1]].append(v)
            elif len(dato) > 2:
                filters[dato[0]][dato[1]] = [v]
            else:
                filters[dato[0]][dato[1]] = v
    return _Pagination(**q, filters=filters)


Pagination = Annotated[_Pagination, Depends(pagination_dependency)]
CurrentUser = Annotated[UserDep, Depends(get_current_user)]
'''


def app_api_deps_minimal(ctx: ProjectContext) -> str:
    return '''from typing import Annotated
from pydantic import BaseModel
from utils.json_web_token import get_current_user
from fastapi import Depends, Request


class UserDep(BaseModel):
    cod_persona: int | None = None
    cod_empresa: int | None = None


class _Pagination(BaseModel):
    total: int | None = 0
    current: int | None = 1
    page_size: int | None = 10
    field: str | None = None
    order: str | None = "desc"
    cod_empresa: int | None = None
    search: str | None = ""
    filters: dict | None = {}


async def pagination_dependency(request: Request) -> _Pagination:
    q = dict(request.query_params)
    return _Pagination(**q, filters={})


Pagination = Annotated[_Pagination, Depends(pagination_dependency)]
CurrentUser = Annotated[UserDep, Depends(get_current_user)]
'''


def app_controllers_database_connection(ctx: ProjectContext) -> str:
    return f'''"""
Conexión a BD usada por los controllers (pybernate).
"""
from pybernate_orm.controllers.base_controller import DatabaseConnection
from app.db.database import get_db


class ProjectDatabaseConnection(DatabaseConnection):
    def __init__(self, default_database: str = "{ctx.db_name}"):
        self.default_database = default_database

    def get_connection(self, database_name: str = None):
        db_name = database_name or self.default_database
        return get_db(db_name)
'''


def app_controllers_orm_controller(ctx: ProjectContext) -> str:
    return '''"""
Controller genérico ORM (master/detail) sobre pybernate.
"""
import datetime
from decimal import Decimal
from pybernate_orm.controllers import FastAPIController
from .database_connection import ProjectDatabaseConnection


class ORMController(FastAPIController):
    def __init__(self, object_name, pagination=None):
        db_connection = ProjectDatabaseConnection()
        super().__init__(
            object_name=object_name,
            db_connection=db_connection,
            orm_module_path="orm.common_services.public",
            pagination=pagination,
        )

    def save(self, data):
        pk = super().save(data, master_detail=True)
        return self.get_master_detail(pk)
'''


def app_permissions(ctx: ProjectContext) -> str:
    return '''"""
Permisos: stub por defecto. Sustituir por lógica real (BD, perfiles, etc.).
"""
from app.context import get_user_id


def VerificaPermiso(cod_funcionalidad: int, user_id: int = None) -> bool:
    """Por defecto permite todo. Implementar verificación real según tu modelo."""
    return True


def get_user_permissions(user_id: int = None, use_cache: bool = True):
    """Stub. Devolver dict de funcionalidades permitidas cuando implementes permisos."""
    return {}
'''


def app_helpers_custom_file_manager(ctx: ProjectContext) -> str:
    return '''"""
Gestor de archivos local (y opcionalmente GCS). Por defecto solo local.
"""
import logging
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from settings.config import settings

logger = logging.getLogger("uvicorn.info")


class StoredFile:
    def __init__(self, file_path: Optional[str] = None, filename: str = "unknown", content_type: str = "application/octet-stream", content: Optional[bytes] = None):
        self._file_path = file_path
        self.filename = filename
        self.content_type = content_type
        self._content = content

    def read(self) -> bytes:
        if self._content is not None:
            return self._content
        if self._file_path:
            with open(self._file_path, "rb") as f:
                return f.read()
        return b""


class FileManager:
    default_path = Path(__file__).resolve().parent.parent.parent.parent / "files_store"

    def __init__(self) -> None:
        self.backend = getattr(settings, "STORAGE_BACKEND", "local")
        self._metadata_file = self.default_path / "metadata.txt"

    def _ensure_local(self) -> None:
        self.default_path.mkdir(exist_ok=True)
        if not self._metadata_file.exists():
            self._metadata_file.touch()

    def _save_metadata(self, file_id: str, filename: str, content_type: str) -> None:
        self._ensure_local()
        with open(self._metadata_file, "a", encoding="utf-8") as f:
            f.write(f"{file_id}|{filename}|{content_type}\\n")

    def _get_metadata(self, file_id: str) -> Optional[tuple]:
        if not self._metadata_file.exists():
            return None
        with open(self._metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3 and parts[0] == file_id:
                    return parts[1], parts[2]
        return None

    def _remove_metadata(self, file_id: str) -> None:
        if not self._metadata_file.exists():
            return
        with open(self._metadata_file, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip().split("|")[0] != file_id]
        with open(self._metadata_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def get_file(self, file_id: str, folder: str = "") -> Optional[StoredFile]:
        self._ensure_local()
        file_path = self.default_path / file_id
        if not file_path.exists():
            return None
        meta = self._get_metadata(file_id)
        if not meta:
            return None
        filename, content_type = meta
        return StoredFile(str(file_path), filename, content_type)

    def delete_file(self, file_id: str, folder: str = "") -> bool:
        self._ensure_local()
        file_path = self.default_path / file_id
        if not file_path.exists():
            return False
        file_path.unlink()
        self._remove_metadata(file_id)
        return True

    def get_public_url(self, file_id: str, folder: str = "", expiration_minutes: int = 60, signed: bool = True) -> Optional[str]:
        if self.backend != "gcs":
            return None
        return None
'''


def app_api_routes_auth(ctx: ProjectContext) -> str:
    if ctx.template == "minimal":
        return '''from fastapi import APIRouter
from app.models.userLogin import UserLogin

router = APIRouter()


@router.post("/login")
async def login(request_data: UserLogin):
    # TODO: implementar lógica de login (BD, JWT)
    return {"message": "Login", "token": "example_token"}


@router.get("/logout")
async def logout():
    return {"message": "Logout"}
'''
    return '''from fastapi import APIRouter
from orm.common_services.public.cms_usuario import cms_usuario
from app.models.userLogin import UserLogin
from pybernate_orm.cache import get_cms_class
from settings.config import settings
from app.db.database import get_db
from datetime import datetime
from utils.json_web_token import generate_token
router = APIRouter()


@router.post("/login")
async def login(request_data: UserLogin):
    usr = get_cms_class(settings.USER_CLASS)
    ret = __login(usr(cnx=get_db()), request_data)
    # ret = cms_usuario().login(request_data)
    return ret


@router.get("/logout")
async def logout():
    return {"message": "Logout"}

def __login(self, user: UserLogin):
        usr = get_cms_class(settings.USER_CLASS)(self.cnx)
        setattr(usr, settings.USER_LOGIN, user.login_user)
        password = user.password
        usr =  usr.get()
        if usr._exists:
            # usr = usrs[0]
            # if not user.cod_empresa:
            #     return {"companies": usr.companies_login}
            if getattr(usr, settings.USER_PASSWORD) == password:
                usr.last_login = datetime.now()
                # company = [e for e in usr.companies_login if e['cod_empresa'] == user.cod_empresa][0]
                token = generate_token({**usr.dict, "cod_empresa": 1}, remember=user.remember)
                return {"user": usr.dict, "token": token, "company": 1}
            else:
                raise Exception("Password incorrecto")
        else:
            raise Exception("Usuario no existe")
        #Lógica de Login
        pass'''


def app_api_routes_generic_master(ctx: ProjectContext) -> str:
    return '''from fastapi import APIRouter
from app.controllers.orm_controller import ORMController
from app.api.deps import Pagination

router = APIRouter()


@router.get("/{path}")
async def get_all(path: str, pagination: Pagination):
    return ORMController(path, pagination=pagination).get_all()


@router.get("/{path}/{pk}")
async def get_one(path: str, pk: int):
    return ORMController(path).get_one(pk)


@router.post("/{path}")
async def save(path: str, data: dict):
    return ORMController(path).save(data)


@router.delete("/{path}")
async def delete(path: str, data: dict):
    return ORMController(path).delete(data)
'''


def app_api_routes_generic_md(ctx: ProjectContext) -> str:
    return '''"""
Generic Master-Detail Routes

This module provides generic routes that work with any controller that follows
the enhanced master-detail pattern. It automatically discovers and instantiates
the appropriate controller based on the entity name.

Examples:
- GET /generic_md/empleado/123 -> Uses EmpleadoController.get_master_detail(123)
- GET /generic_md/cargo/456 -> Uses CargoController.get_master_detail(456)  
- GET /generic_md/nacionalidad/789 -> Uses NacionalidadController.get_master_detail(789)
- POST /generic_md/producto -> Uses ProductoController.save(data)
"""

import importlib
from typing import Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from starlette import status

from app.api.deps import Pagination


router = APIRouter()


def get_controller_class(entity_name: str):
    """
    Dynamically import and return the controller class for the given entity.
    
    Args:
        entity_name: Name of the entity (e.g., "empleado", "cargo", "nacionalidad")
        
    Returns:
        Controller class
        
    Raises:
        HTTPException: If controller not found or cannot be imported
    """
    try:
        # Try to import the controller module
        controller_module_name = f"app.controllers.orm_controllers.controller_{entity_name}"
        controller_module = importlib.import_module(controller_module_name)
        
        # Get the controller class name (capitalize first letter + "Controller")
        controller_class_name = f"Controller{entity_name.replace('_', '').capitalize()}"
        controller_class = getattr(controller_module, controller_class_name)
        
        return controller_class
        
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Controller for entity '{entity_name}' not found. Expected: {controller_module_name}"
        )
    except AttributeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Controller class '{controller_class_name}' not found in module {controller_module_name}"
        )


def create_controller_instance(entity_name: str, pagination: Optional[Pagination] = None):
    """
    Create an instance of the appropriate controller.
    
    Args:
        entity_name: Name of the entity
        pagination: Optional pagination configuration
        rut_company: Optional company RUT for multi-tenant scenarios
        
    Returns:
        Controller instance
    """
    controller_class = get_controller_class(entity_name)
    controller = controller_class(pagination=pagination)
    
    return controller


@router.get("/{entity_name}")
async def get_all_entities(
    entity_name: str, 
    pagination: Pagination 
):
    """
    Get all records for any entity with pagination and grid layout.
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        pagination: Pagination parameters
        rut_company: Optional company RUT for multi-tenant scenarios
    
    Returns:
        Paginated list of records with form structure
        
    Examples:
        GET /generic_md/empleado?page=1&page_size=10
        GET /generic_md/cargo?page=2&page_size=20&rut_company=12345678-9
        GET /generic_md/nacionalidad
    """
    try:
        controller = create_controller_instance(entity_name, pagination)
        return controller.get_master()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving {entity_name} records: {str(e)}"
        )


@router.get("/{entity_name}/details/{pk}")
async def get_entity_master_detail(
    entity_name: str,
    pk: Union[int | str]
):
    """
    Get master-detail structure for any entity using enhanced BaseController method.
    
    This route automatically uses the intelligent get_master_detail method that:
    - Detects advanced layout configurations automatically
    - Uses PyBernate Master-Detail Controller when appropriate
    - Falls back to legacy processing for backward compatibility
    - Processes PyBerField layouts in detail_config correctly
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        pk: Primary key value of the record
        rut_company: Optional company RUT for multi-tenant scenarios
    
    Returns:
        Complete master-detail structure with header and detail data
        
    Examples:
        GET /generic_md/empleado/details/12
        GET /generic_md/producto/details/789
    """
    try:
        controller = create_controller_instance(entity_name)
        return controller.get_master_detail(pk)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error retrieving {entity_name} with ID {pk}: {str(e)}"
        )


@router.post("/{entity_name}/details/{pk}")
async def create_entity(
    entity_name: str,
    pk: Union[int, str],
    data: Dict[str, Any]
):
    """
    Create a new record for any entity and return master-detail structure.
    
    Uses the enhanced save method that automatically returns master-detail
    structure using the intelligent get_master_detail method.
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        data: Record data to save
        rut_company: Optional company RUT for multi-tenant scenarios
    
    Returns:
        Complete master-detail structure of the created record
        
    Examples:
        POST /generic_md/empleado
        POST /generic_md/cargo?rut_company=12345678-9
        POST /generic_md/producto
    """
    try:
        controller = create_controller_instance(entity_name)
        return controller.save(data)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating {entity_name}: {str(e)}"
        )

@router.get("/{entity_name}/export")
async def export_entity_excel(
    entity_name: str,
    pagination: Pagination 
):
    """
    Export all records for an entity as Excel file using get_excel_records.
    """
    try:
        pagination.page_size = 100000000
        controller = create_controller_instance(entity_name, pagination=pagination)
        # Obtener el modelo principal del controlador
        excel_path = controller.get_excel()
        return FileResponse(excel_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"{entity_name}.xlsx")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error exportando {entity_name}: {str(e)}")


@router.put("/{entity_name}")
async def update_entity(
    entity_name: str,
    data: Dict[str, Any]
):
    """
    Update an existing record for any entity and return master-detail structure.
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        data: Record data to update (must include primary key)
    
    Returns:
        Complete master-detail structure of the updated record
    """
    try:
        controller = create_controller_instance(entity_name)
        return controller.save(data)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating {entity_name}: {str(e)}"
        )


@router.delete("/{entity_name}")
async def delete_entity(
    entity_name: str,
    data: Dict[str, Any]
):
    """
    Delete a record for any entity.
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        data: Record data to delete (must include primary key)
    
    Returns:
        Updated list of all records
    """
    try:
        controller = create_controller_instance(entity_name)
        return controller.delete(data)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting {entity_name}: {str(e)}"
        )


@router.get("/{entity_name}/form")
async def get_entity_form_structure(
    entity_name: str
):
    """
    Get form structure for any entity (useful for dynamic form generation).
    
    Args:
        entity_name: Name of the entity (empleado, cargo, nacionalidad, etc.)
        rut_company: Optional company RUT for multi-tenant scenarios
    
    Returns:
        Form structure with field definitions
    """
    try:
        controller = create_controller_instance(entity_name)
        
        # Get form structure from the controller's layout
        if hasattr(controller, 'layout') and controller.layout:
            # Use controller's layout for form structure
            form_data = controller.get_all()
            return {"form": form_data.get("form", [])}
        else:
            # Fallback to basic ORM form
            return {"form": controller.orm.get_form()}
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving form structure for {entity_name}: {str(e)}"
        )



@router.get("/")
async def list_available_entities():
    """
    List all available entities that have controllers.
    
    Returns:
        List of available entity names
    """
    try:
        import os
        import glob
        
        # Get all controller files
        controllers_path = "/Users/vbenitez/CodigoFuente/xrrhh_back/app/controllers"
        controller_files = glob.glob(f"{controllers_path}/controller_*.py")
        
        entities = []
        for file_path in controller_files:
            filename = os.path.basename(file_path)
            # Extract entity name from controller_<entity>.py
            if filename.startswith("controller_") and filename.endswith(".py"):
                entity_name = filename[11:-3]  # Remove "controller_" and ".py"
                entities.append(entity_name)
        
        return {
            "available_entities": sorted(entities),
            "usage_examples": {
                "list_all": "/generic_md/{entity_name}",
                "master_detail": "/generic_md/{entity_name}/details/{pk}",
                "create": "POST /generic_md/{entity_name}",
                "update": "PUT /generic_md/{entity_name}",
                "delete": "DELETE /generic_md/{entity_name}",
                "form_structure": "/generic_md/{entity_name}/form"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing available entities: {str(e)}"
        )'''


def app_api_routes_selects(ctx: ProjectContext) -> str:
    return '''"""Selects / EntryCompletion para frontend."""
from fastapi import APIRouter, Query
from typing import Optional
import json
from app.controllers.orm_controller import ORMController
from app.api.deps import Pagination
from pybernate_orm.queryBuilder import eq, gt, lt, lk, ilk, inn

router = APIRouter()


@router.get("/{path}")
async def get(path: str, filter: Optional[str] = Query(None), filter_in: Optional[str] = Query(None), search: Optional[str] = Query(None)):
    obj = ORMController(path).orm
    query = obj.query.fields(f"{obj.table_descripcion} as label", f"{obj.table_id} as value")
    if filter:
        try:
            d = json.loads(filter) if isinstance(filter, str) else filter
            for k, v in d.items():
                query = query.where(eq(k, v))
        except json.JSONDecodeError:
            pass
    if filter_in:
        try:
            d = json.loads(filter_in) if isinstance(filter_in, str) else filter_in
            for k, vals in d.items():
                if isinstance(vals, list):
                    query = query.where(inn(k, vals))
        except json.JSONDecodeError:
            pass
    if search:
        query = query.where(ilk(obj.table_descripcion, search))
    return query.get()
'''


def app_api_routes_menus(ctx: ProjectContext) -> str:
    return '''"""Rutas de menú para el frontend. Personalizar según tu app."""
from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()


class RouteItem(BaseModel):
    type: str
    key: str
    label: str
    icon: str
    insideBar: bool
    path: Optional[str] = None
    props: Optional[dict] = None
    children: Optional[List["RouteItem"]] = None


RouteItem.model_rebuild()


@router.get("/routes")
async def get_routes(profile: Optional[str] = None):
    """Estructura de rutas/menú. Sustituir por tu lógica (BD, permisos, etc.)."""
    return {"routes": [{"type": "route", "path": "/home", "key": "home", "label": "Inicio", "icon": "MdHome", "insideBar": True}]}
'''


def app_api_routes_files(ctx: ProjectContext) -> str:
    return '''"""Servir archivos (avatars, documentos). Requiere STORAGE_BACKEND en settings."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.helpers.custom.file_manager import FileManager
from settings.config import settings

router = APIRouter()


@router.get("/{folder}/{file_id}")
async def get_file(folder: str, file_id: str):
    fm = FileManager()
    stored = fm.get_file(file_id, folder=folder)
    if not stored:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return Response(content=stored.read(), media_type=stored.content_type, headers={"Content-Disposition": f'inline; filename="{stored.filename}"'})


@router.get("/{folder}/{file_id}/url")
async def get_file_url(folder: str, file_id: str, expiration_minutes: int = 60):
    if getattr(settings, "STORAGE_BACKEND", "local") != "gcs":
        return {"url": f"/api/files/{folder}/{file_id}"}
    fm = FileManager()
    url = fm.get_public_url(file_id, folder=folder, expiration_minutes=expiration_minutes)
    if not url:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return {"url": url}


@router.delete("/{folder}/{file_id}")
async def delete_file(folder: str, file_id: str):
    fm = FileManager()
    if not fm.delete_file(file_id, folder=folder):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return {"message": "Archivo eliminado", "file_id": file_id}
'''


def app_context(ctx: ProjectContext) -> str:
    return '''"""
Global Request Context using contextvars.
"""
from contextvars import ContextVar
from typing import Optional
from app.api.deps import UserDep

_current_user_ctx: ContextVar[Optional[UserDep]] = ContextVar("current_user", default=None)


def set_current_user(user: UserDep) -> None:
    _current_user_ctx.set(user)


def get_current_user_context() -> Optional[UserDep]:
    return _current_user_ctx.get()


def clear_current_user() -> None:
    _current_user_ctx.set(None)
'''


def app_models_user_login(ctx: ProjectContext) -> str:
    return '''from pydantic import BaseModel


class UserLogin(BaseModel):
    login_user: str
    password: str
    remember: bool = False
    cod_empresa: int | None = None
'''


def app_models_buttons(ctx: ProjectContext) -> str:
    return '''"""Modelos de botones para grids y formularios master-detail (compatible con pybernate / frontend)."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ButtonMaster(BaseModel):
    """Botón en la vista maestro / grid."""

    model_config = ConfigDict(extra="allow")

    title: str
    icon: str
    action: Optional[str] = None
    path: Optional[str] = None
    danger: bool = False
    only_selected_rows: bool = False


class ButtonMD(BaseModel):
    """Botón en el detalle (master-detail)."""

    model_config = ConfigDict(extra="allow")

    title: str
    icon: str
    path: Optional[str] = None
    variant: Optional[str] = None
    action: Optional[str] = None


def create_button_master(
    *,
    title: str,
    icon: str,
    action: Optional[str] = None,
    path: Optional[str] = None,
    danger: bool = False,
    only_selected_rows: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    return ButtonMaster(
        title=title,
        icon=icon,
        action=action,
        path=path,
        danger=danger,
        only_selected_rows=only_selected_rows,
        **extra,
    ).model_dump()


def create_button_md(
    *,
    title: str,
    icon: str,
    path: Optional[str] = None,
    variant: Optional[str] = None,
    action: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    return ButtonMD(
        title=title,
        icon=icon,
        path=path,
        variant=variant,
        action=action,
        **extra,
    ).model_dump()
'''


def app_helpers_constants(ctx: ProjectContext) -> str:
    return '''TOKEN_MISSING_IN_HEADERS = "Token missing in Headers"
INVALID_TOKEN = "Invalid Token"
EXPIRED_TOKEN = "Session Expired. Please start again!"
'''


def utils_json_web_token_full(ctx: ProjectContext) -> str:
    return '''from jwt import encode, exceptions, decode
from datetime import datetime, timedelta, date
from fastapi import Header
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_417_EXPECTATION_FAILED
from app.helpers.constants import INVALID_TOKEN, EXPIRED_TOKEN, TOKEN_MISSING_IN_HEADERS
from pybernate_orm.cache import get_cms_class
from settings.config import settings


def exp_date(dias: int):
    return datetime.now() + timedelta(days=dias)


def serialize_data(data: dict) -> dict:
    serialized = {}
    for key, value in data.items():
        if isinstance(value, (datetime, date)):
            serialized[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized[key] = serialize_data(value)
        elif isinstance(value, list):
            serialized[key] = [
                item.isoformat() if isinstance(item, (datetime, date)) else item
                for item in value
            ]
        else:
            serialized[key] = value
    return serialized


def generate_token(data: dict, remember: bool | None = False):
    serialized_data = serialize_data(data)
    token = encode(
        payload={**serialized_data, "exp": exp_date(365 if remember else 2)},
        key=settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token


def validate_token(token, output=False):
    try:
        if output:
            return decode(token, key=settings.SECRET_KEY, algorithms=["HS256"])
        decode(token, key=settings.SECRET_KEY, algorithms=["HS256"])
    except exceptions.DecodeError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN)
    except exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_417_EXPECTATION_FAILED, detail=EXPIRED_TOKEN)


async def get_current_user(Authorization: str = Header(None)):
    if Authorization is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail=TOKEN_MISSING_IN_HEADERS
        )
    try:
        scheme, token = Authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN)
        token_info = validate_token(token, output=True)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=str(e))
    from app.api.deps import UserDep
    return UserDep(**token_info)
'''


def utils_json_web_token_minimal(ctx: ProjectContext) -> str:
    return '''from jwt import encode, exceptions, decode
from datetime import datetime, timedelta
from fastapi import Header
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_417_EXPECTATION_FAILED
from app.helpers.constants import INVALID_TOKEN, EXPIRED_TOKEN, TOKEN_MISSING_IN_HEADERS
from settings.config import settings


def exp_date(dias: int):
    return datetime.now() + timedelta(days=dias)


def generate_token(data: dict, remember: bool = False):
    payload = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in data.items()}
    payload["exp"] = exp_date(365 if remember else 2)
    return encode(payload=payload, key=settings.SECRET_KEY, algorithm="HS256")


def validate_token(token, output=False):
    try:
        if output:
            return decode(token, key=settings.SECRET_KEY, algorithms=["HS256"])
        decode(token, key=settings.SECRET_KEY, algorithms=["HS256"])
    except exceptions.DecodeError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN)
    except exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_417_EXPECTATION_FAILED, detail=EXPIRED_TOKEN)


async def get_current_user(Authorization: str = Header(None)):
    if Authorization is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail=TOKEN_MISSING_IN_HEADERS
        )
    scheme, token = Authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN)
    token_info = validate_token(token, output=True)
    from app.api.deps import UserDep
    return UserDep(**token_info)
'''


def middlewares_user_context(ctx: ProjectContext) -> str:
    if not ctx.include_redis:
        return ""
    return '''"""
User Context Middleware - sets current user from JWT in request context.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.context import set_current_user, clear_current_user
from utils.json_web_token import validate_token


class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                scheme, token = auth_header.split()
                if scheme.lower() == "bearer":
                    token_info = validate_token(token, output=True)
                    from app.api.deps import UserDep
                    set_current_user(UserDep(**token_info))
        except Exception:
            pass
        response = await call_next(request)
        clear_current_user()
        return response
'''


def orm_init(ctx: ProjectContext) -> str:
    return '''import os

def reverse_engineer(generate_controllers=False, force_overwrite_controllers=False):
    from pybernate_orm.pyBernateGenClass import pyBernateGenClass
    from settings.config import settings
    gc = pyBernateGenClass()
    print("settings.POSTGRES_SERVER", settings.POSTGRES_SERVER)
    print("settings.POSTGRES_PORT", settings.POSTGRES_PORT)
    print("settings.POSTGRES_DB", settings.POSTGRES_DB)
    print("settings.POSTGRES_USER", settings.POSTGRES_USER)
    print("settings.POSTGRES_PASSWORD", settings.POSTGRES_PASSWORD)
    gc.set_path(os.path.dirname(os.path.abspath(__file__)))
    gc.make_coneccion(settings.POSTGRES_SERVER, settings.POSTGRES_PORT, settings.POSTGRES_DB, settings.POSTGRES_USER, settings.POSTGRES_PASSWORD)
    gc.reverse_ingeneer(generate_controllers=generate_controllers, force_overwrite_controllers=force_overwrite_controllers)
    gc.cursor.close()
    gc.cnx.close()

def gen_single_controller(table_name):
    from pybernate_orm.pyBernateGenClass import pyBernateGenClass
    from settings.config import settings
    gc = pyBernateGenClass()
    gc.set_path(os.path.dirname(os.path.abspath(__file__)))
    gc.make_coneccion(settings.POSTGRES_SERVER, settings.POSTGRES_PORT, settings.POSTGRES_DB, settings.POSTGRES_USER, settings.POSTGRES_PASSWORD)
    gc.gen_single_controller(table_name, force_overwrite=True)
    gc.cursor.close()
    gc.cnx.close()

def single_reverse_engineer(table_name, generate_controllers=False, force_overwrite_controllers=False):
    from pybernate_orm.pyBernateGenClass import pyBernateGenClass
    from settings.config import settings
    gc = pyBernateGenClass()
    gc.set_path(os.path.dirname(os.path.abspath(__file__)))
    gc.make_coneccion(settings.POSTGRES_SERVER, settings.POSTGRES_PORT, settings.POSTGRES_DB, settings.POSTGRES_USER, settings.POSTGRES_PASSWORD)
    gc.reverse_ingeneer_single(table_name, generate_controllers=generate_controllers, force_overwrite_controllers=force_overwrite_controllers)
    gc.cursor.close()
    gc.cnx.close()

if __name__ == "__main__":
    reverse_engineer(generate_controllers=True, force_overwrite_controllers=False)
'''


def celery_app(ctx: ProjectContext) -> str:
    if not ctx.include_celery:
        return ""
    return f'''from celery import Celery
from settings.config import settings

celery_app = Celery(
    "{ctx.slug}",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.example_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
)
'''


def redis_client(ctx: ProjectContext) -> str:
    if not ctx.include_redis:
        return ""
    return '''from redis import Redis
from settings.config import settings

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
'''


def tasks_example(ctx: ProjectContext) -> str:
    if not ctx.include_celery:
        return ""
    return '''from app.celery_app import celery_app

@celery_app.task
def example_task():
    return {"status": "success", "message": "Tarea completada"}
'''


def dockerfile(ctx: ProjectContext) -> str:
    return '''FROM python:3.12-slim
WORKDIR /app
RUN pip install poetry
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \\
    && poetry lock 2>/dev/null || true \\
    && poetry install --no-interaction --no-ansi --no-root
COPY . .
EXPOSE %s
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "%s", "--reload"]
''' % (ctx.port, str(ctx.port))


def docker_compose(ctx: ProjectContext) -> str:
    prefix = ctx.container_name_prefix
    services = f'''
  api:
    build: .
    container_name: {prefix}_api
    env_file: .env
    ports:
      - "{ctx.port}:{ctx.port}"
    volumes:
      - .:/app
    depends_on:
      - db
  db:
    image: postgres:15-alpine
    env_file: .env
    container_name: {prefix}_db
    environment:
      POSTGRES_USER: ${{POSTGRES_USER}}
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD}}
      POSTGRES_DB: ${{POSTGRES_DB}}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
'''
    if ctx.include_redis:
        services += f'''
  redis:
    image: redis:latest
    container_name: {prefix}_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
'''
    if ctx.include_celery:
        services += f'''
  celery_worker:
    build: .
    container_name: {prefix}_celery_worker
    env_file: .env
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    command: celery -A app.celery worker --loglevel=info
'''
    volumes = "postgres_data:"
    if ctx.include_redis:
        volumes += "\n  redis_data:"
    return f'''services:
{services}
volumes:
  {volumes}

networks:
  default:
    name: {ctx.slug}-net
'''


def gitignore(ctx: ProjectContext) -> str:
    return '''__pycache__/
.idea/
*.pyc
*.pyo
.env
.env.*
.venv/
venv/
*.log
.DS_Store
'''


def makefile(ctx: ProjectContext) -> str:
    return f'''IMAGE_NAME ?= {ctx.slug}
IMAGE_TAG ?= latest

run:
\tdocker compose up

build:
\tdocker compose up --build

docker-build:
\tdocker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
'''


def shell_plus(ctx: ProjectContext) -> str:
    deps = "settings"
    if ctx.include_redis:
        deps += ", redis_client, celery_app"
    return f'''from app.db.database import get_db
from settings.config import settings

try:
    import IPython
    IPython.start_ipython(
        argv=[],
        user_ns={{"settings": settings, "get_db": get_db}},
    )
except ImportError:
    print("Instala ipython: poetry add --group dev ipython")
'''


def readme(ctx: ProjectContext) -> str:
    user_ctx_readme = ""
    if ctx.include_redis:
        user_ctx_readme = """
## User Context Middleware (`run.py`)

Con Redis, `run.py` incluye el **User Context Middleware** en un bloque **comentado** por defecto.

- **Mantén comentado** hasta haber ejecutado el **reverse engineering** y existir el módulo CMS del usuario (`orm.common_services.<schema>.cms_<USER_CLASS>`, según `USER_CLASS` en `settings/config.py`).
- **Descomenta** las líneas del middleware cuando ese módulo exista; si lo activas antes, el arranque puede fallar con errores de importación (por ejemplo `No module named '...cms_persona'`).

"""
    return f'''# {ctx.project_name}

Backend generado con create-back-cli.
{user_ctx_readme}
## Requisitos

- Python 3.12+
- PostgreSQL 15+
- Redis (opcional, para cache/Celery)
- Poetry

## Rutas

Las rutas vienen **comentadas** en `app/api/main.py`. Activa solo las que necesites descomentando la línea correspondiente:

- **auth**: login/logout
- **generic_master (gm)**: CRUD genérico por path (tablas maestras)
- **generic_md (gmd)**: CRUD master-detail por entidad (requiere controllers en `app/controllers/orm_controllers/`)
- **selects**: opciones para combos/EntryCompletion
- **menus**: estructura de menú para el frontend
- **files**: servir archivos (avatars, documentos; usa `app/helpers/custom/file_manager`)

Al agregar nuevos routers (en `app/api/routes/`), impórtalos en `main.py` y añade su `include_router` comentado hasta que decidas activarlo.

## Desarrollo

```bash
cp .env.example .env
# Editar .env con tus valores
poetry install
poetry run uvicorn run:app --reload --port {ctx.port}
```

## Docker

```bash
docker compose up --build
```

API: http://localhost:{ctx.port}
Docs: http://localhost:{ctx.port}/docs
'''


def vscode_launch(ctx: ProjectContext) -> str:
    return f'''{{
    "version": "0.2.0",
    "configurations": [
        {{
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": ["run:app", "--reload", "--host", "0.0.0.0", "--port", "{ctx.port}"],
            "jinja": true
        }}
    ]
}}
'''


def pre_commit(ctx: ProjectContext) -> str:
    return '''repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        language_version: python3.12
        args: [--line-length=88]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
'''