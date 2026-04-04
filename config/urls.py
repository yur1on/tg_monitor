from django.contrib import admin
from django.urls import path
import config.admin  # noqa

urlpatterns = [
    path("admin/", admin.site.urls),
]