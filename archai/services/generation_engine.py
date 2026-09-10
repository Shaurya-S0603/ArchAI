"""Operator-controlled experimental inference with an observable, dependency-free fallback."""

from archai.services.layout_generator import generate_layouts

BASELINE = "deterministic-baseline"
EXPERIMENTAL = "experimental-neural"


def load_experimental_engine(run):
    from archai_ml.inference import NeuralEngine

    return NeuralEngine(run)


def init_app(app):
    requested = app.config["ARCHAI_GENERATOR"]
    if requested not in (BASELINE, EXPERIMENTAL):
        raise ValueError("Unknown ARCHAI_GENERATOR setting.")
    state = {"requested": requested, "engine": None, "reason": None}
    if requested == EXPERIMENTAL:
        try:
            state["engine"] = load_experimental_engine(app.config["ARCHAI_MODEL_RUN"])
        except (ImportError, OSError, ValueError, RuntimeError, KeyError, TypeError):
            state["reason"] = "engine_unavailable"
            app.logger.warning("Experimental generator unavailable; using deterministic baseline.")
    app.extensions["archai_generator"] = state


def generate_for_app(app, brief):
    state = app.extensions["archai_generator"]
    reason = state["reason"]
    if state["engine"] is not None:
        try:
            layouts = state["engine"](brief)
            from archai_ml.diversity import validate_concepts

            validate_concepts(layouts, brief)
            return layouts, {"requested": state["requested"], "used": EXPERIMENTAL,
                             "fallback": False, "reason": None}
        except Exception:
            # This boundary protects the web request from optional engine faults.
            # Research evaluation deliberately does not catch programming errors.
            reason = "candidate_rejected"
            app.logger.exception("Experimental generator failed; using deterministic baseline.")
    return generate_layouts(brief), {"requested": state["requested"], "used": BASELINE,
                                    "fallback": state["requested"] != BASELINE, "reason": reason}
