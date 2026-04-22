from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('chat/', views.chat_page, name='chat_page'),
    path('products/<str:product_type>/', views.product_list, name='product_list'),
    path('products/<str:product_type>/<int:product_id>/', views.product_detail, name='product_detail'),

    path('customer/register/', views.customer_register, name='customer_register'),
    path('customer/login/', views.customer_login, name='customer_login'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/items/<int:item_id>/update/', views.cart_item_update, name='cart_item_update'),
    path('cart/items/<int:item_id>/delete/', views.cart_item_delete, name='cart_item_delete'),
    path('cart/checkout/', views.checkout, name='checkout'),

    path('staff/login/', views.staff_login, name='staff_login'),
    path('staff/logout/', views.staff_logout, name='staff_logout'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),

    path('staff/products/<str:product_type>/create/', views.staff_product_create, name='staff_product_create'),
    path('staff/products/<str:product_type>/<int:product_id>/edit/', views.staff_product_edit, name='staff_product_edit'),
    path('staff/products/<str:product_type>/<int:product_id>/delete/', views.staff_product_delete, name='staff_product_delete'),

    path('api/chat/message/', views.chat_message_proxy, name='chat_message_proxy'),
]
