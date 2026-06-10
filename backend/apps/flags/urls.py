from django.urls import path

from .views import FlagsView

urlpatterns = [
    path("", FlagsView.as_view(), name="flags"),
]
