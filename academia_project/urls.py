# academia_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from ui.auth_views import RoleAwareLoginView  # 👈

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", RoleAwareLoginView.as_view(), name="login"),  # 👈
    path("accounts/logout/", __import__("django.contrib.auth.views", fromlist=["LogoutView"]).LogoutView.as_view(), name="logout"),
        path('panel/horarios/', include(('academia_horarios.urls', 'academia_horarios'), namespace='academia_horarios')),
    path(
        "panel/cargar/",
        RedirectView.as_view(pattern_name="academia_horarios:cargar_horario", permanent=False),
    ),
    path("", include("ui.urls")),
    path("", include("academia_core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
