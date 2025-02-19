from flask import render_template, blueprints
from flask_login import login_required

from src.utils import get_system_info
from src.config import app

system_health_bp = blueprints.Blueprint("system_health", __name__)

@app.route("/system_health")
@login_required
def system_health():
    system_info = get_system_info()
    return render_template("system_health.html", system_info=system_info)
