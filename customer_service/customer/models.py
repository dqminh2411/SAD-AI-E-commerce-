from django.db import models


class Customer(models.Model):
	id = models.CharField(max_length=36, primary_key=True)
	email = models.EmailField(unique=True)
	full_name = models.CharField(max_length=255)
	password_hash = models.CharField(max_length=255)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'customers'


class CustomerToken(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
	token = models.CharField(max_length=64, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'customer_tokens'
