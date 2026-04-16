from django.urls import path

from .views import LoginView, OrdersProxyView, ProductProxyView, ProfileView

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/profile/', ProfileView.as_view(), name='profile'),
    path('api/proxy/products/<path:path>', ProductProxyView.as_view(), name='proxy_products_path'),
    path('api/proxy/products/', ProductProxyView.as_view(), name='proxy_products'),
    path('api/proxy/orders/<path:path>', OrdersProxyView.as_view(), name='proxy_orders_path'),
    path('api/proxy/orders/', OrdersProxyView.as_view(), name='proxy_orders'),
]
