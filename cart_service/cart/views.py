import os
from decimal import Decimal

import requests
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
	AddItemSerializer,
	CartSerializer,
	OrderSerializer,
	UpdateItemSerializer,
)


CUSTOMER_SERVICE_URL = os.environ.get('CUSTOMER_SERVICE_URL', 'http://customer-service:8001')
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8002')


def _get_token_from_request(request):
	auth = request.headers.get('Authorization', '')
	if auth.startswith('Token '):
		return auth.removeprefix('Token ').strip()
	return None


def _get_customer_id(request) -> str | None:
	token_value = _get_token_from_request(request)
	if not token_value:
		return None
	r = requests.get(
		CUSTOMER_SERVICE_URL.rstrip('/') + '/api/profile/',
		headers={'Authorization': f'Token {token_value}'},
		timeout=10,
	)
	if r.status_code != 200:
		return None
	data = r.json() if r.content else {}
	cid = str(data.get('id') or '').strip()
	return cid or None


def _get_or_create_open_cart(customer_id: str) -> Cart:
	cart = Cart.objects.filter(customer_id=customer_id, status='open').order_by('-created_at').first()
	if cart:
		return cart
	return Cart.objects.create(customer_id=customer_id, status='open')


def _fetch_product(product_type: str, product_id: int):
	# Unified product service
	r = requests.get(PRODUCT_SERVICE_URL.rstrip('/') + f'/api/v1/products/{product_id}/', timeout=10)
	if r.status_code != 200:
		return None
	data = r.json()
	images = data.get('images') or []
	image_url = data.get('thumbnail_url')
	if not image_url and isinstance(images, list) and images:
		image_url = images[0].get('url')

	base_price = data.get('base_price')
	try:
		unit_price = Decimal(str(base_price))
	except Exception:
		unit_price = Decimal('0')

	return {
		'id': data.get('id'),
		'name': data.get('name', ''),
		'image_url': image_url,
		'price': unit_price,
	}


class CartView(APIView):
	def get(self, request):
		customer_id = _get_customer_id(request)
		if not customer_id:
			return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

		cart = _get_or_create_open_cart(customer_id)
		return Response(CartSerializer(cart).data)


class CartItemAddView(APIView):
	def post(self, request):
		customer_id = _get_customer_id(request)
		if not customer_id:
			return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

		serializer = AddItemSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		product_type = serializer.validated_data['product_type']
		product_id = serializer.validated_data['product_id']
		quantity = serializer.validated_data['quantity']

		product = _fetch_product(product_type, product_id)
		if not product:
			return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

		cart = _get_or_create_open_cart(customer_id)
		existing = CartItem.objects.filter(
			cart=cart, product_type=product_type, product_id=product_id
		).first()
		if existing:
			existing.quantity = existing.quantity + quantity
			existing.save(update_fields=['quantity'])
		else:
			CartItem.objects.create(
				cart=cart,
				product_type=product_type,
				product_id=product_id,
				product_name=product.get('name', ''),
				image_url=product.get('image_url'),
				unit_price=product.get('price', Decimal('0')),
				quantity=quantity,
			)

		return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartItemUpdateDeleteView(APIView):
	def patch(self, request, item_id: int):
		customer_id = _get_customer_id(request)
		if not customer_id:
			return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

		serializer = UpdateItemSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		quantity = serializer.validated_data['quantity']

		item = CartItem.objects.filter(id=item_id, cart__customer_id=customer_id, cart__status='open').first()
		if not item:
			return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
		item.quantity = quantity
		item.save(update_fields=['quantity'])

		return Response(CartSerializer(item.cart).data)

	def delete(self, request, item_id: int):
		customer_id = _get_customer_id(request)
		if not customer_id:
			return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

		item = CartItem.objects.filter(id=item_id, cart__customer_id=customer_id, cart__status='open').first()
		if not item:
			return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
		cart = item.cart
		item.delete()
		return Response(CartSerializer(cart).data)


class CheckoutView(APIView):
	@transaction.atomic
	def post(self, request):
		customer_id = _get_customer_id(request)
		if not customer_id:
			return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

		cart = Cart.objects.filter(customer_id=customer_id, status='open').order_by('-created_at').first()
		if not cart:
			return Response({'detail': 'No open cart'}, status=status.HTTP_400_BAD_REQUEST)

		items = list(CartItem.objects.filter(cart=cart))
		if not items:
			return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

		total = sum((item.unit_price * item.quantity for item in items), Decimal('0'))
		order = Order.objects.create(customer_id=customer_id, total_amount=total)

		for item in items:
			OrderItem.objects.create(
				order=order,
				product_type=item.product_type,
				product_id=item.product_id,
				product_name=item.product_name,
				image_url=item.image_url,
				unit_price=item.unit_price,
				quantity=item.quantity,
			)

		cart.status = 'checked_out'
		cart.save(update_fields=['status'])
		CartItem.objects.filter(cart=cart).delete()

		return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrdersView(APIView):
	def get(self, request):
		# Staff can call this without customer auth; customers will still be restricted.
		customer_id = request.query_params.get('customer_id')
		qs = Order.objects.all().order_by('-created_at')
		if customer_id:
			qs = qs.filter(customer_id=str(customer_id).strip())
		return Response(OrderSerializer(qs, many=True).data)
