"""ArchAI Flask application factory."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("ARCHAI_SECRET_KEY", "development-only-change-me"),
        DATABASE=os.environ.get(
            "ARCHAI_DATABASE", str(Path(app.instance_path) / "archai.sqlite3")
        ),
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        ARCHAI_GENERATOR=os.environ.get("ARCHAI_GENERATOR", "deterministic-baseline"),
        ARCHAI_MODEL_RUN=os.environ.get("ARCHAI_MODEL_RUN"),
    )
    if test_config:
        app.config.update(test_config)

    from archai.database import init_app as init_database
    from archai.routes import api, pages
    from archai.services.generation_engine import init_app as init_generator

    app.register_blueprint(pages)
    app.register_blueprint(api, url_prefix="/api/v1")
    init_database(app)
    init_generator(app)

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "Request payload must be smaller than 2 MB."}), 413

    return app
