from django.contrib.auth.hashers import check_password
from rest_framework import serializers

from .models import StaffUser


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        try:
            staff = StaffUser.objects.get(username=username)
        except StaffUser.DoesNotExist:
            raise serializers.ValidationError('Invalid username or password')

        if not check_password(password, staff.password_hash):
            raise serializers.ValidationError('Invalid username or password')

        attrs['staff'] = staff
        return attrs


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffUser
        fields = ['id', 'username', 'full_name', 'is_admin', 'created_at']
