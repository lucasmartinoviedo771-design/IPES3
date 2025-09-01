# ui/context_processors.py
import unicodedata
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from .menu import for_role

# --- helpers de rol ---
ROLE_MAP = {
    "admin": "Admin", "administrador": "Admin",
    "bedel": "Bedel",
    "secretaria": "Secretaria", "secretaría": "Secretaria",
    "docente": "Docente",
    "estudiante": "Estudiante", "alumno": "Estudiante",
}
def _norm(s):  # quita acentos y lower
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()

def _infer_role_from_user(user):
    if not user or not user.is_authenticated:
        return ""
    if getattr(user, "is_superuser", False):
        return "Admin"
    for g in user.groups.all():
        hit = ROLE_MAP.get(_norm(g.name))
        if hit:
            return hit
    return ""

# --- resolver paths de menú ---
def _resolve_menu_paths(items):
    for it in items:
        url_name = it.pop("url_name", None)
        if url_name and "path" not in it:
            try:
                it["path"] = reverse(url_name)
            except NoReverseMatch:
                it["path"] = "#"
        if "url" not in it and "path" in it:
            it["url"] = it["path"]
        if isinstance(it.get("children"), list):
            _resolve_menu_paths(it["children"])

def menu(request):
    # leer rol desde sesión (ambas claves) o inferir del user
    role = (
        request.session.get("rol_actual")
        or request.session.get("active_role")
        or _infer_role_from_user(getattr(request, "user", None))
    )

    sections = for_role(role) or []
    # clonar para no mutar el original
    resolved = []
    for s in sections:
        node = dict(s)  # copia superficial
        _resolve_menu_paths(node.get("children", []))
        if node.get("url_name") and not node.get("path"):
            try:
                node["path"] = reverse(node["url_name"])
                node["url"] = node["path"]
            except Exception:
                node["path"] = node["url"] = "#"
        resolved.append(node)

    # ⚠️ devolvemos AMBOS nombres por compatibilidad con templates
    return {"menu": resolved, "menu_sections": resolved}

def role_from_request(request):
    # unificar claves de sesión y exponer 'user_role'
    role = request.session.get("active_role") or request.session.get("rol_actual")
    if not role:
        role = _infer_role_from_user(getattr(request, "user", None))
    if role:
        request.session["active_role"] = role
        request.session["rol_actual"] = role
    return {"user_role": role, "role": role, "active_role": role}

def ui_globals(request):
    return {"APP_NAME": "IPES", "APP_BRAND": "IPES", "DEBUG": settings.DEBUG}