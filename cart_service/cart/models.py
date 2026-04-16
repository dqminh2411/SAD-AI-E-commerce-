from django.db import models


class Cart(models.Model):
	customer_id = models.CharField(max_length=36)
	status = models.CharField(max_length=32)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'carts'


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	product_type = models.CharField(max_length=32)
	product_id = models.BigIntegerField()
	product_name = models.CharField(max_length=255)
	image_url = models.TextField(null=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	quantity = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'cart_items'


class Order(models.Model):
	customer_id = models.CharField(max_length=36)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		managed = False
		db_table = 'orders'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE)
	product_type = models.CharField(max_length=32)
	product_id = models.BigIntegerField()
	product_name = models.CharField(max_length=255)
	image_url = models.TextField(null=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	quantity = models.IntegerField()

	class Meta:
		managed = False
		db_table = 'order_items'
