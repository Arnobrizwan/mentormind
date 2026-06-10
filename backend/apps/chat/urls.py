from django.urls import path

from .views import CourseChatHistoryView

urlpatterns = [
    path("courses/<slug:slug>/messages/", CourseChatHistoryView.as_view(), name="chat-history"),
]
