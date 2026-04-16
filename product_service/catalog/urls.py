from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrandListView, CategoryListView, ProductLookupView, ProductTypeListView, ProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
	path('', include(router.urls)),
	path('brands/', BrandListView.as_view(), name='brand-list'),
	path('categories/', CategoryListView.as_view(), name='category-list'),
	path('product-types/', ProductTypeListView.as_view(), name='producttype-list'),
	path('products/lookup/', ProductLookupView.as_view(), name='product-lookup'),
]
