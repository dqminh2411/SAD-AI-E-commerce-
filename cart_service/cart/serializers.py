from rest_framework import serializers

from .models import Cart, CartItem, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'product_type', 'product_id', 'product_name', 'image_url', 'unit_price', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'customer_id', 'status', 'created_at', 'items']

    def get_items(self, obj):
        qs = getattr(obj, 'items', None)
        if qs is not None:
            return CartItemSerializer(qs.all().order_by('id'), many=True).data
        return CartItemSerializer(CartItem.objects.filter(cart=obj).order_by('id'), many=True).data


class AddItemSerializer(serializers.Serializer):
    product_type = serializers.ChoiceField(choices=['laptop', 'clothes'])
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_type', 'product_id', 'product_name', 'image_url', 'unit_price', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'customer_id', 'total_amount', 'created_at', 'items']

    def get_items(self, obj):
        return OrderItemSerializer(OrderItem.objects.filter(order=obj).order_by('id'), many=True).data
