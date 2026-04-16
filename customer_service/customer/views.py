import re
import secrets

from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer, CustomerToken
from .serializers import CustomerProfileSerializer, LoginSerializer, RegisterSerializer


def _get_token_from_request(request):
	auth = request.headers.get('Authorization', '')
	if auth.startswith('Token '):
		return auth.removeprefix('Token ').strip()
	return None


class RegisterView(APIView):
	def post(self, request):
		serializer = RegisterSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		email = serializer.validated_data['email']
		full_name = serializer.validated_data['full_name']
		password = serializer.validated_data['password']

		if Customer.objects.filter(email=email).exists():
			return Response({'detail': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)

		with transaction.atomic():
			# Generate next user id like US_001 / US-001 by scanning current max.
			max_num = 0
			sep = '_'
			for cid in Customer.objects.select_for_update().values_list('id', flat=True):
				m = re.match(r"^US([-_])(\d+)$", str(cid or '').strip())
				if not m:
					continue
				num = int(m.group(2))
				if num > max_num:
					max_num = num
					sep = m.group(1)
			new_id = f"US{sep}{max_num + 1:03d}"

			customer = Customer.objects.create(
				id=new_id,
				email=email,
				full_name=full_name,
				password_hash=make_password(password),
			)

		token_value = secrets.token_hex(32)
		CustomerToken.objects.create(customer=customer, token=token_value)

		return Response(
			{
				'customer': CustomerProfileSerializer(customer).data,
				'token': token_value,
			},
			status=status.HTTP_201_CREATED,
		)


class LoginView(APIView):
	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		customer = serializer.validated_data['customer']

		token_value = secrets.token_hex(32)
		CustomerToken.objects.create(customer=customer, token=token_value)

		return Response(
			{
				'customer': CustomerProfileSerializer(customer).data,
				'token': token_value,
			}
		)


class ProfileView(APIView):
	def get(self, request):
		token_value = _get_token_from_request(request)
		if not token_value:
			return Response({'detail': 'Missing token'}, status=status.HTTP_401_UNAUTHORIZED)

		try:
			token = CustomerToken.objects.select_related('customer').get(token=token_value)
		except CustomerToken.DoesNotExist:
			return Response({'detail': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

		return Response(CustomerProfileSerializer(token.customer).data)
