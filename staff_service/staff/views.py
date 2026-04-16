import os
import secrets

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StaffToken
from .serializers import LoginSerializer, StaffProfileSerializer


def _get_token_from_request(request):
	auth = request.headers.get('Authorization', '')
	if auth.startswith('Token '):
		return auth.removeprefix('Token ').strip()
	return None


def _require_staff(request):
	token_value = _get_token_from_request(request)
	if not token_value:
		return None, Response({'detail': 'Missing token'}, status=status.HTTP_401_UNAUTHORIZED)

	try:
		token = StaffToken.objects.select_related('staff').get(token=token_value)
	except StaffToken.DoesNotExist:
		return None, Response({'detail': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

	return token.staff, None


class LoginView(APIView):
	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		staff = serializer.validated_data['staff']

		token_value = secrets.token_hex(32)
		StaffToken.objects.create(staff=staff, token=token_value)

		return Response({'staff': StaffProfileSerializer(staff).data, 'token': token_value})


class ProfileView(APIView):
	def get(self, request):
		staff, error = _require_staff(request)
		if error:
			return error
		return Response(StaffProfileSerializer(staff).data)


class ProxyView(APIView):
	"""Minimal proxy for staff-managed operations."""

	upstream_base_url = None

	def dispatch(self, request, *args, **kwargs):
		staff, error = _require_staff(request)
		if error:
			return error
		return super().dispatch(request, *args, **kwargs)

	def _upstream_url(self, path):
		if not self.upstream_base_url:
			raise RuntimeError('Proxy upstream_base_url not configured')
		return self.upstream_base_url.rstrip('/') + '/' + path.lstrip('/')

	def get(self, request, path=''):
		r = requests.get(self._upstream_url(path), params=request.query_params, timeout=10)
		return Response(r.json() if r.content else None, status=r.status_code)

	def post(self, request, path=''):
		r = requests.post(self._upstream_url(path), json=request.data, timeout=10)
		return Response(r.json() if r.content else None, status=r.status_code)

	def put(self, request, path=''):
		r = requests.put(self._upstream_url(path), json=request.data, timeout=10)
		return Response(r.json() if r.content else None, status=r.status_code)

	def patch(self, request, path=''):
		r = requests.patch(self._upstream_url(path), json=request.data, timeout=10)
		return Response(r.json() if r.content else None, status=r.status_code)

	def delete(self, request, path=''):
		r = requests.delete(self._upstream_url(path), timeout=10)
		return Response(r.json() if r.content else None, status=r.status_code)

class ProductProxyView(ProxyView):
	upstream_base_url = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8002')


class OrdersProxyView(ProxyView):
	upstream_base_url = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8004')
