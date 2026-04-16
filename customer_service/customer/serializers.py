from django.contrib.auth.hashers import check_password
from rest_framework import serializers

from .models import Customer


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=6, write_only=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password')

        if not check_password(password, customer.password_hash):
            raise serializers.ValidationError('Invalid email or password')

        attrs['customer'] = customer
        return attrs


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'email', 'full_name', 'created_at']
