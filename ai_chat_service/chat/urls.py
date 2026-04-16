from django.urls import path

from .views import ChatHealthView, ChatMessageView

urlpatterns = [
    path('health/', ChatHealthView.as_view(), name='chat_health'),
    path('message/', ChatMessageView.as_view(), name='chat_message'),
]
