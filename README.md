# Create Back CLI

CLI para generar un proyecto backend basado en la estructura de **xrrhh_back** (FastAPI, PostgreSQL, Redis, Celery, pybernate_orm).

## Datos que solicita el CLI

| Dato | Descripción | Default |
|------|-------------|---------|
| **Nombre del proyecto** | Nombre legible (ej: `Mi Proyecto Back`) | - |
| **Slug del proyecto** | Nombre para carpetas/paquetes (ej: `mi_proyecto_back`) | Inferido del nombre |
| **Descripción** | Descripción corta del proyecto | "" |
| **Autor** | Nombre o "Nombre <email>" | - |
| **Puerto** | Puerto HTTP de la API | 8888 |
| **Nombre BD por defecto** | Nombre de la base PostgreSQL por defecto | = slug |
| **Incluir Celery** | Colas de tareas en background | true |
| **Incluir Redis** | Cache y broker para Celery | true |
| **URL pybernate_orm** | Repo git del submodule (siempre se enlaza; vacío = URL por defecto) | opcional |
| **Plantilla** | `minimal` (solo API + auth) o `full` (como xrrhh_back) | full |
| **Crear .venv** | Crear `.venv` en el proyecto e instalar dependencias (poetry o pip) | true |

## Qué genera el CLI

- **Raíz:** `pyproject.toml`, `run.py`, `.gitignore`, `.pre-commit-config.yaml`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md`, `shell_plus.py`
- **settings:** `config.py` con variables de entorno
- **app:** `__init__.py`, `api/main.py`, `api/deps.py`, `api/routes/auth.py`, `db/database.py`, `context.py`, `models/userLogin.py`, `permissions.py`
- **middlewares:** `user_context.py`, `jwt_verify.py`
- **utils:** `json_web_token.py`, `__init__.py`, y otros helpers básicos
- **orm:** `__init__.py` con `reverse_engineer()` y carpetas `common_services/public/`
- **Opción full:** `celery_app.py`, `redis_client.py`, `tasks/example_tasks.py`, más rutas de ejemplo
- **.vscode:** `launch.json` para depurar FastAPI
- **pybernate_orm:** siempre se enlaza como submodule (`git submodule add` con URL por defecto)
- **.venv:** por defecto se crea un entorno virtual en el proyecto y se instalan dependencias (con `poetry install` o, si no hay poetry, con `python -m venv .venv` + `pip install -r requirements.txt`). Así el proyecto no depende del .venv del CLI ni del sistema.

## Uso

### Con Poetry (recomendado)

```bash
cd create_back_cli
poetry install
poetry run create-back
```

**Si `poetry run` da error con el nombre (espacios o "unexpected extra arguments")**, ejecuta el CLI con el venv directo o como módulo:

```bash
# Opción A: venv directo (tras poetry install)
.venv/bin/create-back --name "SubCheck Back2" --slug subcheck_back2 -o ..

# Opción B: como módulo Python
poetry run python -m create_back_cli.cli --name "SubCheck Back2" --slug subcheck_back2 -o ..
```

Preguntará: nombre del proyecto, slug, autor, etc. Para usar valores por defecto sin preguntas:

```bash
poetry run create-back --name "Mi API" --slug mi_api_back --output .. --force
```

### Con pip + venv

```bash
cd create_back_cli
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m create_back_cli.cli --help
python -m create_back_cli.cli --name "Mi API" --slug mi_api_back -o ..
```

### Instalación global (disponible en cualquier directorio)

Para tener `create-back` disponible en cualquier directorio sin activar un venv ni usar `poetry run`.

**Con pyenv** (instalar en el Python global de pyenv):

```bash
cd create_back_cli
# Si `pip` no está en el PATH, usa el módulo pip con el Python de pyenv:
python -m pip install -e .
# (asegúrate de que `python` es el de pyenv: pyenv which python)
```

Comprueba que el `create-back` que se usa es el de pyenv:

```bash
which create-back    # debería ser algo como ~/.pyenv/shims/create-back
create-back --help
```

Desde cualquier ruta ya puedes ejecutar:

```bash
create-back --name "Mi API" --slug mi_api_back -o .
```

**Sin pyenv:** usa el `pip` del Python donde quieras el comando (ej. `python3 -m pip install -e .`).

### Opciones principales

| Opción | Descripción |
|--------|-------------|
| `-n, --name` | Nombre del proyecto |
| `-s, --slug` | Slug (carpeta/paquete) |
| `-o, --output` | Directorio donde crear (se crea subcarpeta con el slug) |
| `-p, --port` | Puerto de la API (default 8888) |
| `--no-celery` | No incluir Celery |
| `--no-redis` | No incluir Redis |
| `--pybernate URL` | URL del repo pybernate_orm (opcional; por defecto se enlaza siempre) |
| `-t minimal \| full` | Plantilla minimal o full |
| `-f, --force` | Sobrescribir sin preguntar |
| `--no-venv` | No crear .venv ni instalar dependencias (útil si quieres hacerlo a mano) |

**Nota (plantilla full):** La ruta de auth usa `cms_persona` del ORM. El submodule pybernate_orm se enlaza siempre; después ejecuta `python orm/__init__.py` (o el script de reverse engineering) para generar las clases ORM antes de usar login real.
