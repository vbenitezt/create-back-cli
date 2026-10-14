# -*- coding: utf-8 -*-
"""Generador de archivos del proyecto backend."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .context import ProjectContext
from . import templates as T

# URL por defecto del submodule pybernate_orm (siempre se enlaza)
DEFAULT_PYBERNATE_URL = "https://github.com/vbenitezt/pybernate-orm"

console = Console()


def _slug_from_name(name: str) -> str:
    """Convierte 'Mi Proyecto Back' -> mi_proyecto_back."""
    s = re.sub(r"[^\w\s-]", "", name.lower())
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s or "backend"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _add_pybernate_submodule(output_dir: Path, url: str) -> None:
    """Inicializa el repo git si hace falta y añade el submodule pybernate_orm."""
    output_dir = output_dir.resolve()
    submodule_path = output_dir / "pybernate_orm"
    if submodule_path.exists():
        console.print("[dim]pybernate_orm ya existe, omitiendo git submodule add[/dim]")
        return
    is_git = (output_dir / ".git").exists()
    try:
        if not is_git:
            subprocess.run(
                ["git", "init"],
                cwd=output_dir,
                check=True,
                capture_output=True,
            )
            console.print("[dim]Inicializado repositorio git[/dim]")
        result = subprocess.run(
            ["git", "submodule", "add", url, "pybernate_orm"],
            cwd=output_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Submodule pybernate_orm añadido correctamente[/green]")
        else:
            console.print(
                f"[yellow]No se pudo añadir el submodule (¿git instalado?): {result.stderr or result.stdout}[/yellow]"
            )
            console.print(
                "[dim]Puedes añadirlo manualmente: git submodule add "
                f"{url} pybernate_orm[/dim]"
            )
    except FileNotFoundError:
        console.print(
            "[yellow]Git no encontrado. Añade el submodule manualmente:[/yellow]"
        )
        console.print(f"[dim]  git submodule add {url} pybernate_orm[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Error al inicializar git: {e}[/yellow]")
        console.print(f"[dim]  git submodule add {url} pybernate_orm[/dim]")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Lista de (path_relativo, función_plantilla)
FILE_MAP: list[tuple[str, Callable[[ProjectContext], str]]] = [
    ("pyproject.toml", T.pyproject_toml),
    ("requirements.txt", T.requirements_txt),
    ("run.py", T.run_py),
    (".env.example", T.env_example),
    (".gitignore", T.gitignore),
    (".pre-commit-config.yaml", T.pre_commit),
    ("Makefile", T.makefile),
    ("Dockerfile", T.dockerfile),
    ("docker-compose.yml", T.docker_compose),
    ("README.md", T.readme),
    ("shell_plus.py", T.shell_plus),
    ("settings/config.py", T.settings_config),
    ("app/__init__.py", T.app_init),
    ("app/db/__init__.py", lambda _: ""),
    ("app/db/database.py", T.app_db_database),
    ("app/api/__init__.py", lambda _: ""),
    ("app/api/main.py", T.app_api_main),
    ("app/api/deps.py", None),  # resuelto según template
    ("app/api/routes/__init__.py", lambda _: ""),
    ("app/api/routes/auth.py", T.app_api_routes_auth),
    ("app/api/routes/generic_master.py", T.app_api_routes_generic_master),
    ("app/api/routes/generic_md.py", T.app_api_routes_generic_md),
    ("app/api/routes/selects.py", T.app_api_routes_selects),
    ("app/api/routes/menus.py", T.app_api_routes_menus),
    ("app/api/routes/files.py", T.app_api_routes_files),
    ("app/controllers/__init__.py", lambda _: ""),
    ("app/controllers/database_connection.py", T.app_controllers_database_connection),
    ("app/controllers/orm_controller.py", T.app_controllers_orm_controller),
    ("app/controllers/orm_controllers/__init__.py", lambda _: ""),
    ("app/permissions.py", T.app_permissions),
    ("app/helpers/custom/__init__.py", lambda _: ""),
    ("app/helpers/custom/file_manager.py", T.app_helpers_custom_file_manager),
    ("app/context.py", T.app_context),
    ("app/models/__init__.py", lambda _: ""),
    ("app/models/userLogin.py", T.app_models_user_login),
    ("app/models/buttons.py", T.app_models_buttons),
    ("app/helpers/__init__.py", lambda _: ""),
    ("app/helpers/constants.py", T.app_helpers_constants),
    ("utils/__init__.py", lambda _: ""),
    ("utils/json_web_token.py", None),  # resuelto según template
    ("middlewares/__init__.py", lambda _: ""),
    ("middlewares/user_context.py", T.middlewares_user_context),
    ("middlewares/jwt_verify.py", lambda _: '"""JWT verification (APIRoute)."""\n'),
    ("orm/__init__.py", T.orm_init),
    ("orm/common_services/public/__init__.py", lambda _: ""),
    (".vscode/launch.json", T.vscode_launch),
]

# Archivos condicionales: (path, función, condición)
CONDITIONAL = [
    ("app/celery_app.py", T.celery_app, lambda ctx: ctx.include_celery),
    ("app/redis_client.py", T.redis_client, lambda ctx: ctx.include_redis),
    ("app/tasks/__init__.py", lambda _: "", lambda ctx: ctx.include_celery),
    ("app/tasks/example_tasks.py", T.tasks_example, lambda ctx: ctx.include_celery),
]


def resolve_deps(ctx: ProjectContext) -> str:
    if ctx.template == "minimal":
        return T.app_api_deps_minimal(ctx)
    return T.app_api_deps_full(ctx)


def resolve_jwt(ctx: ProjectContext) -> str:
    if ctx.template == "minimal":
        return T.utils_json_web_token_minimal(ctx)
    return T.utils_json_web_token_full(ctx)


def _create_venv(ctx: ProjectContext, output_dir: Path) -> None:
    """Crea .venv en el directorio del proyecto e instala dependencias con pip.

    Se usa siempre ``python -m venv`` (mismo intérprete que ejecuta el CLI) y
    ``pip install -r requirements.txt``, para no depender de que ``poetry`` esté
    en el PATH ni de que ``poetry install`` resuelva sin ``poetry.lock``.
    """
    output_dir = output_dir.resolve()
    venv_path = output_dir / ".venv"
    requirements = output_dir / "requirements.txt"

    if venv_path.exists():
        console.print("[dim].venv ya existe, omitiendo creación[/dim]")
        return

    if sys.platform == "win32":
        pip = venv_path / "Scripts" / "pip.exe"
    else:
        pip = venv_path / "bin" / "pip"

    try:
        r = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        console.print(
            "[yellow]No se pudo invocar Python para crear el venv. "
            "Instala Python y ejecuta en el proyecto: python -m venv .venv[/yellow]"
        )
        return
    except subprocess.TimeoutExpired:
        console.print("[yellow]Creación del venv excedió el tiempo de espera.[/yellow]")
        return

    if r.returncode != 0:
        console.print(f"[yellow]python -m venv falló (código {r.returncode}).[/yellow]")
        if r.stderr:
            console.print(f"[dim]{r.stderr.strip()}[/dim]")
        if r.stdout:
            console.print(f"[dim]{r.stdout.strip()}[/dim]")
        console.print(
            "[dim]Manual: cd proyecto && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt[/dim]"
        )
        return

    console.print("[green].venv creado en el proyecto[/green]")

    if not requirements.is_file():
        console.print(
            "[yellow]No se encontró requirements.txt; instala dependencias a mano en .venv.[/yellow]"
        )
        return

    try:
        subprocess.run(
            [str(pip), "install", "--upgrade", "pip"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        r = subprocess.run(
            [str(pip), "install", "-r", str(requirements.name)],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            console.print("[yellow]pip install -r requirements.txt falló.[/yellow]")
            err = (r.stderr or r.stdout or "").strip()
            if err:
                console.print(f"[dim]{err[-3000:]}[/dim]")
            console.print(
                "[dim]Activa el venv e instala: source .venv/bin/activate && pip install -r requirements.txt[/dim]"
            )
            return
        console.print("[green]Dependencias instaladas en .venv (requirements.txt).[/green]")
    except subprocess.TimeoutExpired:
        console.print("[yellow]pip install excedió el tiempo de espera.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Error instalando dependencias en .venv: {e}[/yellow]")


def generate(ctx: ProjectContext, output_dir: Path, force: bool = False, create_venv: bool = True) -> None:
    """Genera todos los archivos del proyecto en output_dir."""
    output_dir = output_dir.resolve()
    if not force and output_dir.exists() and any(output_dir.iterdir()):
        console.print(
            f"[yellow]El directorio {output_dir} ya existe y no está vacío.[/yellow]"
        )
        if not console.input("¿Sobrescribir? (s/N): ").strip().lower().startswith("s"):
            raise SystemExit(1)
    ensure_dir(output_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generando proyecto...", total=None)
        written = 0

        for rel_path, get_content in FILE_MAP:
            if get_content is None:
                if "deps.py" in rel_path:
                    get_content = resolve_deps
                elif "json_web_token" in rel_path:
                    get_content = resolve_jwt
                else:
                    continue
            content = get_content(ctx)
            if not content and "user_context" in rel_path:
                continue
            path = output_dir / rel_path
            write_file(path, content)
            written += 1

        for rel_path, get_content, cond in CONDITIONAL:
            if not cond(ctx):
                continue
            content = get_content(ctx)
            path = output_dir / rel_path
            write_file(path, content)
            written += 1

        progress.update(task, completed=True)

    # Siempre enlazar el submodule pybernate_orm (URL por defecto o la indicada con --pybernate)
    _add_pybernate_submodule(output_dir, ctx.pybernate_url or DEFAULT_PYBERNATE_URL)

    if create_venv:
        _create_venv(ctx, output_dir)

    console.print(f"[green]Proyecto generado en {output_dir}[/green] ({written} archivos)")
    console.print(f"  cd {output_dir}")
    console.print("  cp .env.example .env")
    if create_venv:
        vpy = (
            output_dir / ".venv" / "Scripts" / "python.exe"
            if sys.platform == "win32"
            else output_dir / ".venv" / "bin" / "python"
        )
        console.print("  # Arranque (venv ya creado en el proyecto):")
        console.print(f"  {vpy} -m uvicorn run:app --reload --port {ctx.port}")
    else:
        console.print("  python -m venv .venv && .venv/bin/pip install -r requirements.txt")
        console.print(f"  .venv/bin/python -m uvicorn run:app --reload --port {ctx.port}  # Linux/macOS")
