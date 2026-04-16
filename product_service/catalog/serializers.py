from rest_framework import serializers

from .models import Brand, Category, Product, ProductImage, ProductType, ProductVariant


class BrandSerializer(serializers.ModelSerializer):
	class Meta:
		model = Brand
		fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
	class Meta:
		model = Category
		fields = ['id', 'parent', 'name', 'slug']


class ProductTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProductType
		fields = ['id', 'code', 'name', 'attribute_schema']


class ProductImageSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProductImage
		fields = ['id', 'url', 'sort_order']


class ProductVariantSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProductVariant
		fields = ['id', 'sku', 'variant_name', 'price_override', 'stock', 'attributes']


class ProductListSerializer(serializers.ModelSerializer):
	product_type = ProductTypeSerializer(read_only=True)
	brand = BrandSerializer(read_only=True)
	category = CategorySerializer(read_only=True)
	thumbnail_url = serializers.SerializerMethodField()
	in_stock = serializers.SerializerMethodField()

	class Meta:
		model = Product
		fields = [
			'id',
			'name',
			'product_type',
			'brand',
			'category',
			'base_price',
			'currency',
			'in_stock',
			'thumbnail_url',
			'created_at',
		]

	def get_thumbnail_url(self, obj: Product):
		img = obj.images.order_by('sort_order', 'id').first()
		return img.url if img else None

	def get_in_stock(self, obj: Product):
		if obj.variants.exists():
			return obj.variants.filter(stock__gt=0).exists()
		return obj.stock > 0


class ProductDetailSerializer(serializers.ModelSerializer):
	product_type = ProductTypeSerializer(read_only=True)
	brand = BrandSerializer(read_only=True)
	category = CategorySerializer(read_only=True)
	images = ProductImageSerializer(many=True, read_only=True)
	variants = ProductVariantSerializer(many=True, read_only=True)

	class Meta:
		model = Product
		fields = [
			'id',
			'name',
			'description',
			'product_type',
			'brand',
			'category',
			'base_price',
			'currency',
			'stock',
			'attributes',
			'images',
			'variants',
			'created_at',
			'updated_at',
		]


class ProductWriteSerializer(serializers.ModelSerializer):
	product_type_code = serializers.CharField(write_only=True)
	brand_name = serializers.CharField(write_only=True)
	category_slug = serializers.CharField(write_only=True)
	image_urls = serializers.ListField(
		child=serializers.URLField(),
		required=False,
		write_only=True,
	)

	class Meta:
		model = Product
		fields = [
			'id',
			'product_type_code',
			'brand_name',
			'category_slug',
			'image_urls',
			'name',
			'description',
			'base_price',
			'currency',
			'stock',
			'attributes',
			'is_active',
			'source_url',
		]

	def create(self, validated_data):
		product_type_code = validated_data.pop('product_type_code')
		brand_name = validated_data.pop('brand_name')
		category_slug = validated_data.pop('category_slug')
		image_urls = validated_data.pop('image_urls', [])

		product_type, _ = ProductType.objects.get_or_create(
			code=product_type_code,
			defaults={'name': product_type_code.title(), 'attribute_schema': {}},
		)
		brand, _ = Brand.objects.get_or_create(name=brand_name)
		category, _ = Category.objects.get_or_create(
			slug=category_slug,
			defaults={'name': category_slug.replace('-', ' ').title()},
		)

		product = Product.objects.create(
			product_type=product_type,
			brand=brand,
			category=category,
			**validated_data,
		)
		if image_urls:
			ProductImage.objects.bulk_create([
				ProductImage(product=product, url=u, sort_order=i)
				for i, u in enumerate(image_urls)
			])
		return product

	def update(self, instance, validated_data):
		# These write-only fields are optional on update.
		product_type_code = validated_data.pop('product_type_code', None)
		brand_name = validated_data.pop('brand_name', None)
		category_slug = validated_data.pop('category_slug', None)
		image_urls = validated_data.pop('image_urls', None)

		if product_type_code:
			instance.product_type, _ = ProductType.objects.get_or_create(
				code=product_type_code,
				defaults={'name': product_type_code.title(), 'attribute_schema': {}},
			)
		if brand_name:
			instance.brand, _ = Brand.objects.get_or_create(name=brand_name)
		if category_slug:
			instance.category, _ = Category.objects.get_or_create(
				slug=category_slug,
				defaults={'name': category_slug.replace('-', ' ').title()},
			)

		for k, v in validated_data.items():
			setattr(instance, k, v)
		instance.save()
		if image_urls is not None:
			ProductImage.objects.filter(product=instance).delete()
			ProductImage.objects.bulk_create([
				ProductImage(product=instance, url=u, sort_order=i)
				for i, u in enumerate(image_urls)
			])
		return instance


class ProductLookupItemSerializer(serializers.Serializer):
	product_id = serializers.IntegerField()
	variant_id = serializers.IntegerField(required=False, allow_null=True)
	quantity = serializers.IntegerField(min_value=1)


class ProductLookupRequestSerializer(serializers.Serializer):
	items = ProductLookupItemSerializer(many=True)
