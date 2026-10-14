# -*- coding: utf-8 -*-
"""CLI create-back: genera un proyecto backend basado en xrrhh_back."""

import shlex
import sys
from pathlib import Path

import click

# Workaround: poetry run a veces pasa todos los argumentos como una sola cadena
if len(sys.argv) == 2 and isinstance(sys.argv[1], str) and " " in sys.argv[1]:
    s = sys.argv[1].strip()
    if s.startswith("-") or "--" in s:
        try:
            sys.argv = [sys.argv[0]] + shlex.split(sys.argv[1])
        except Exception:
            pass

from rich.console import Console
from rich.prompt import Prompt, Confirm

from .context import ProjectContext
from .generator import generate, _slug_from_name

console = Console()


def _prompt_slug(default: str) -> str:
    slug = Prompt.ask("Slug del proyecto (carpetas/paquetes)", default=default)
    return slug.strip() or default


@click.command()
@click.option("--name", "-n", default="", help='Nombre del proyecto. Con espacios: --name="SubCheck Back2"')
@click.option("--slug", "-s", default=None, help="Slug (ej: mi_proyecto_back)")
@click.option("--description", "-d", default="", help="Descripción")
@click.option("--author", "-a", default="", help='Autor (ej: "Tu Nombre <email>")')
@click.option("--output", "-o", type=click.Path(path_type=Path), default=".", help="Directorio donde crear el proyecto")
@click.option("--port", "-p", default=8888, help="Puerto de la API")
@click.option("--db-name", default=None, help="Nombre de la BD por defecto")
@click.option("--no-celery", is_flag=True, help="No incluir Celery")
@click.option("--no-redis", is_flag=True, help="No incluir Redis")
@click.option("--pybernate", default="", help="URL del repo pybernate_orm (opcional)")
@click.option("--template", "-t", default="full", help="Plantilla: minimal o full")
@click.option(
    "--user-class",
    default=None,
    help="USER_CLASS: clase de usuario CMS en settings (ej. usuario, persona)",
)
@click.option(
    "--user-login",
    default=None,
    help="USER_LOGIN: nombre del atributo de login en el modelo (ej. desc_usuario)",
)
@click.option(
    "--user-password",
    default=None,
    help="USER_PASSWORD: nombre del atributo de contraseña en el modelo (ej. password)",
)
@click.option("--force", "-f", is_flag=True, help="Sobrescribir sin preguntar")
@click.option("--no-venv", is_flag=True, help="No crear .venv ni instalar dependencias")
def main(
    name: str,
    slug: str | None,
    description: str,
    author: str,
    output: Path,
    port: int,
    db_name: str | None,
    no_celery: bool,
    no_redis: bool,
    pybernate: str,
    template: str,
    user_class: str | None,
    user_login: str | None,
    user_password: str | None,
    force: bool,
    no_venv: bool,
) -> None:
    """Genera un proyecto backend (FastAPI, PostgreSQL, Redis, Celery) basado en xrrhh_back."""
    name = (name or "").strip()
    if not name:
        name = Prompt.ask("Nombre del proyecto", default="Mi Backend").strip()
    slug_default = _slug_from_name(name)
    slug = (slug or "").strip().replace("-", "_")
    if not slug:
        slug = slug_default or _prompt_slug(slug_default)

    if not author:
        author = Prompt.ask("Autor", default="Developer <dev@example.com>")

    user_class_val = (user_class or "").strip()
    if not user_class_val:
        user_class_val = Prompt.ask(
            "USER_CLASS (clase de usuario CMS, p. ej. usuario o persona)",
            default="usuario",
        ).strip() or "usuario"

    user_login_val = (user_login or "").strip()
    if not user_login_val:
        user_login_val = Prompt.ask(
            "USER_LOGIN (atributo del modelo para el usuario en login, p. ej. desc_usuario)",
            default="desc_usuario",
        ).strip() or "desc_usuario"

    user_password_val = (user_password or "").strip()
    if not user_password_val:
        user_password_val = Prompt.ask(
            "USER_PASSWORD (nombre del atributo de contraseña en el modelo)",
            default="password",
        ).strip() or "password"

    db_name = db_name or slug
    template_ok = template.lower() in ("minimal", "full")
    project_ctx = ProjectContext(
        project_name=name,
        slug=slug,
        description=description or "",
        author=author,
        port=port,
        db_name=db_name,
        include_celery=not no_celery,
        include_redis=not no_redis,
        pybernate_url=(pybernate or "").strip(),
        template="minimal" if template.lower() == "minimal" else "full",
        user_class=user_class_val,
        user_login=user_login_val,
        user_password=user_password_val,
    )

    out = Path(output).resolve() / slug

    console.print(f"\n[bold]Proyecto:[/bold] {name}")
    console.print(f"[bold]Slug:[/bold] {slug}")
    console.print(f"[bold]Salida:[/bold] {out}")
    console.print(f"[bold]Celery:[/bold] {project_ctx.include_celery}")
    console.print(f"[bold]Redis:[/bold] {project_ctx.include_redis}")
    console.print(f"[bold]Plantilla:[/bold] {project_ctx.template}")
    console.print(f"[bold]USER_CLASS:[/bold] {project_ctx.user_class}")
    console.print(f"[bold]USER_LOGIN:[/bold] {project_ctx.user_login}")
    console.print(f"[bold]USER_PASSWORD:[/bold] {project_ctx.user_password}")
    console.print(f"[bold]Crear .venv:[/bold] {not no_venv}\n")

    if not force and out.exists() and any(out.iterdir()):
        if not Confirm.ask("El directorio ya existe. ¿Continuar y sobrescribir?"):
            raise SystemExit(1)

    try:
        generate(project_ctx, out, force=force, create_venv=not no_venv)
    except SystemExit as e:
        raise SystemExit(e.code)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


def app() -> None:
    """Punto de entrada para el script instalado (poetry/setuptools)."""
    main()


if __name__ == "__main__":
    main()
