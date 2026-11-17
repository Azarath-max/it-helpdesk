"""Jinja2 template rendering for transactional email."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "emails"

_html_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
_text_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=False,
)


def render_template(name: str, context: dict[str, object]) -> str:
    """Render a template by its file name."""
    if name.endswith(".html"):
        return _html_env.get_template(name).render(**context)
    return _text_env.get_template(name).render(**context)
