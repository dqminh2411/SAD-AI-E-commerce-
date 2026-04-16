from django.db import models


class ProductType(models.Model):
	code = models.CharField(max_length=50, unique=True)
	name = models.CharField(max_length=255)
	attribute_schema = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"{self.code}"


class Brand(models.Model):
	name = models.CharField(max_length=255, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.name


class Category(models.Model):
	parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['parent']),
		]

	def __str__(self) -> str:
		return self.name


class Product(models.Model):
	product_type = models.ForeignKey(ProductType, on_delete=models.PROTECT, related_name='products')
	brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')	
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')

	name = models.CharField(max_length=255)
	description = models.TextField(blank=True, default='')

	base_price = models.DecimalField(max_digits=12, decimal_places=2)
	currency = models.CharField(max_length=10, default='VND')

	# For products without variants.
	stock = models.IntegerField(default=0)

	attributes = models.JSONField(default=dict, blank=True)
	is_active = models.BooleanField(default=True)

	# Helps keep imports idempotent.
	source_url = models.URLField(max_length=1000, blank=True, null=True, unique=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['product_type', 'is_active', '-created_at']),
			models.Index(fields=['brand']),
			models.Index(fields=['category']),
		]

	def __str__(self) -> str:
		return self.name


class ProductVariant(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
	sku = models.CharField(max_length=100, unique=True)
	variant_name = models.CharField(max_length=255)
	price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	stock = models.IntegerField(default=0)
	attributes = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.sku


class ProductImage(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
	url = models.URLField(max_length=1000)
	sort_order = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['product', 'sort_order']),
		]

	def __str__(self) -> str:
		return self.url
