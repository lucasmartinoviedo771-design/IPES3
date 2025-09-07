import os

from django.conf import settings


def fmt_fecha(d):
    return d.strftime("%d/%m/%Y") if d else ""


def fmt_nota(m):
    if m.nota_num is not None:
        return str(m.nota_num).rstrip("0").rstrip(".")
    return m.nota_texto or ""


# Resolver rutas /media y /static cuando generamos PDF
def link_callback(uri):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        return path
    if uri.startswith(getattr(settings, "STATIC_URL", "/static/")):
        static_root = getattr(settings, "STATIC_ROOT", "")
        if static_root:
            return os.path.join(static_root, uri.replace(settings.STATIC_URL, ""))
    # Si es una URL absoluta http(s), xhtml2pdf suele bloquear; devolvemos tal cual.
    return uri
