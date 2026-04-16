from django.urls import path

from .views import CartItemAddView, CartItemUpdateDeleteView, CartView, CheckoutView, OrdersView

urlpatterns = [
    path('api/cart/', CartView.as_view(), name='cart'),
    path('api/cart/items/', CartItemAddView.as_view(), name='cart_item_add'),
    path('api/cart/items/<int:item_id>/', CartItemUpdateDeleteView.as_view(), name='cart_item_update_delete'),
    path('api/checkout/', CheckoutView.as_view(), name='checkout'),
    path('api/orders/', OrdersView.as_view(), name='orders'),
]
