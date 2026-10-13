"""Única rota funcional da base; não acessa estruturas nem arquivos."""

from flask import Blueprint, render_template

bp = Blueprint("publicas", __name__)


@bp.get("/")
def inicio() -> str:
    return render_template("index.html")
