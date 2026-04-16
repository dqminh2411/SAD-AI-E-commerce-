from django.db import models


class StaffUser(models.Model):
	username = models.CharField(max_length=150, unique=True)
	full_name = models.CharField(max_length=255)
	password_hash = models.CharField(max_length=255)
	is_admin = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'staff_users'


class StaffToken(models.Model):
	staff = models.ForeignKey(StaffUser, on_delete=models.CASCADE)
	token = models.CharField(max_length=64, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'staff_tokens'
