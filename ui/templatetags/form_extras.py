import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def addclass(field, css):
    if hasattr(field, "field") and hasattr(field.field, "widget"):
        existing = field.field.widget.attrs.get("class", "")
        field.field.widget.attrs["class"] = (existing + " " + css).strip()
        return field
    html = str(field)
    if not html.strip():
        return html
    if 'class="' in html:
        html = html.replace('class="', f'class="{css} ', 1)
    else:
        html = re.sub(r"(<\w+)(\s|>)", rf'\1 class="{css}"\2', html, count=1)
    return mark_safe(html)
