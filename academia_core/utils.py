# academia_core/utils.py
from typing import Any

from django.apps import apps


def get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Versión segura de getattr, que también devuelve el default si el valor es None.
    """
    val = getattr(obj, key, default)
    return default if val is None else val


def get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None
