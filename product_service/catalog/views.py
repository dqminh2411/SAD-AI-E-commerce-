import re

from django.db import connection
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchVector
from rest_framework import generics, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Brand, Category, Product, ProductType, ProductVariant
from .serializers import (
	BrandSerializer,
	CategorySerializer,
	ProductDetailSerializer,
	ProductListSerializer,
	ProductLookupRequestSerializer,
	ProductTypeSerializer,
	ProductWriteSerializer,
)


class DefaultPagination(PageNumberPagination):
	page_size = 12
	page_size_query_param = 'page_size'
	max_page_size = 50


def _build_prefix_tsquery(term: str) -> str:
	parts = re.findall(r"[\w]+", (term or "").lower())
	parts = [p for p in parts if p]
	if not parts:
		return ""
	return " & ".join(f"{p}:*" for p in parts)


class ProductViewSet(viewsets.ModelViewSet):
	queryset = Product.objects.all().select_related('product_type', 'brand', 'category').prefetch_related('images', 'variants')
	pagination_class = DefaultPagination

	def get_serializer_class(self):
		if self.action in ('create', 'update', 'partial_update'):
			return ProductWriteSerializer
		if self.action == 'retrieve':
			return ProductDetailSerializer
		return ProductListSerializer

	def get_queryset(self):
		qs = super().get_queryset().filter(is_active=True)

		term = (self.request.query_params.get('q') or '').strip()
		product_type = (self.request.query_params.get('product_type') or '').strip().upper()
		category_id = self.request.query_params.get('category_id')
		brand_id = self.request.query_params.get('brand_id')
		min_price = self.request.query_params.get('min_price')
		max_price = self.request.query_params.get('max_price')
		in_stock = self.request.query_params.get('in_stock')
		sort = (self.request.query_params.get('sort') or 'newest').strip()

		if product_type:
			qs = qs.filter(product_type__code=product_type)
		if category_id and str(category_id).isdigit():
			qs = qs.filter(category_id=int(category_id))
		if brand_id and str(brand_id).isdigit():
			qs = qs.filter(brand_id=int(brand_id))
		if min_price:
			try:
				qs = qs.filter(base_price__gte=min_price)
			except Exception:
				pass
		if max_price:
			try:
				qs = qs.filter(base_price__lte=max_price)
			except Exception:
				pass

		if term:
			# Prefer Postgres full-text + prefix, but fall back to icontains.
			if connection.vendor == 'postgresql':
				tsquery = _build_prefix_tsquery(term)
				fts = SearchQuery(tsquery, search_type='raw') if tsquery else SearchQuery(term)
				vector = SearchVector('name', 'description', 'brand__name')
				qs = qs.annotate(_sv=vector).filter(
					Q(_sv=fts)
					| Q(name__icontains=term)
					| Q(brand__name__icontains=term)
					| Q(description__icontains=term)
				)
			else:
				qs = qs.filter(
					Q(name__icontains=term)
					| Q(brand__name__icontains=term)
					| Q(description__icontains=term)
				)

		if in_stock in ('true', 'false'):
			want = in_stock == 'true'
			if want:
				qs = qs.filter(Q(stock__gt=0) | Q(variants__stock__gt=0)).distinct()
			else:
				qs = qs.exclude(Q(stock__gt=0) | Q(variants__stock__gt=0)).distinct()

		if sort == 'price_asc':
			qs = qs.order_by('base_price', '-created_at')
		elif sort == 'price_desc':
			qs = qs.order_by('-base_price', '-created_at')
		elif sort == 'name_asc':
			qs = qs.order_by('name', '-created_at')
		elif sort == 'name_desc':
			qs = qs.order_by('-name', '-created_at')
		else:
			qs = qs.order_by('-created_at')

		return qs


class BrandListView(generics.ListAPIView):
	queryset = Brand.objects.all().order_by('name')
	serializer_class = BrandSerializer


class CategoryListView(generics.ListAPIView):
	queryset = Category.objects.select_related('parent').all().order_by('name')
	serializer_class = CategorySerializer


class ProductTypeListView(generics.ListAPIView):
	queryset = ProductType.objects.all().order_by('code')
	serializer_class = ProductTypeSerializer


class ProductLookupView(APIView):
	def post(self, request):
		ser = ProductLookupRequestSerializer(data=request.data)
		ser.is_valid(raise_exception=True)

		results = []
		for item in ser.validated_data['items']:
			product_id = item['product_id']
			variant_id = item.get('variant_id')

			product = Product.objects.filter(id=product_id, is_active=True).select_related('product_type').first()
			if not product:
				results.append({
					'product_id': product_id,
					'variant_id': variant_id,
					'ok': False,
					'error': 'PRODUCT_NOT_FOUND',
				})
				continue

			unit_price = product.base_price
			available_stock = product.stock
			sku = None

			if variant_id is not None:
				variant = ProductVariant.objects.filter(id=variant_id, product_id=product.id).first()
				if not variant:
					results.append({
						'product_id': product_id,
						'variant_id': variant_id,
						'ok': False,
						'error': 'VARIANT_NOT_FOUND',
					})
					continue
				sku = variant.sku
				available_stock = variant.stock
				if variant.price_override is not None:
					unit_price = variant.price_override

			results.append({
				'product_id': product.id,
				'variant_id': variant_id,
				'ok': True,
				'name': product.name,
				'sku': sku,
				'unit_price': {
					'amount': str(unit_price),
					'currency': product.currency,
				},
				'available_stock': available_stock,
				'product_type': product.product_type.code,
			})

		return Response({'items': results}, status=status.HTTP_200_OK)
