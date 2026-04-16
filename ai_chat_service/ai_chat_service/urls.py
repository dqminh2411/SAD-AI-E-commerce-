from django.urls import include, path

urlpatterns = [
    path('api/v1/chat/', include('chat.urls')),
]
