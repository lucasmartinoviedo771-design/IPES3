from typing import Any
from django.contrib.auth.models import AnonymousUser

# Intentamos reutilizar la implementación “oficial” existente si ya la tenés:
try:
    # En tu repo aparece resolverse desde ui.auth_views
    from ui.auth_views import resolve_role as _resolve_role  # type: ignore
except Exception:  # fallback genérico si no existe
    def _resolve_role(user) -> str:  # type: ignore
        # Toma el primer grupo como “rol”, si no hay grupos: 'user'
        try:
            name = next(iter(user.groups.values_list("name", flat=True)))
            return name or "user"
        except Exception:
            return "anon"

def role_of(obj: Any) -> str:
    """
    Acepta request o user y devuelve el “rol” (string).
    Si está anónimo o None -> 'anon'.
    """
    user = getattr(obj, "user", obj)
    if user is None or isinstance(user, AnonymousUser):
        return "anon"
    return _resolve_role(user)