import uuid

from django.utils import timezone
from rest_framework import serializers

from .models import InteractionEvent


EVENT_TYPES = ('view', 'search', 'add_to_cart', 'purchase', 'chat')
PRODUCT_TYPES = ('LAPTOP', 'CLOTHES')


class InteractionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionEvent
        fields = [
            'event_id',
            'user_id',
            'session_id',
            'event_type',
            'product_id',
            'query_text',
            'duration_ms',
            'created_at',
            'page',
            'product_type',
            'metadata',
            'neo4j_synced',
            'neo4j_synced_at',
            'neo4j_error',
        ]


class InteractionEventCreateSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=64, required=False, allow_blank=False)
    user_id = serializers.CharField(max_length=64)
    session_id = serializers.CharField(max_length=128, required=False, allow_null=True, allow_blank=True)

    event_type = serializers.ChoiceField(choices=EVENT_TYPES)

    product_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    query_text = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    duration_ms = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    created_at = serializers.DateTimeField(required=False)
    page = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=64)
    product_type = serializers.ChoiceField(choices=PRODUCT_TYPES, required=False, allow_null=True)

    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        et = attrs.get('event_type')
        pid = attrs.get('product_id')
        qt = (attrs.get('query_text') or '').strip()

        if et in ('view', 'add_to_cart', 'purchase') and not pid:
            raise serializers.ValidationError({'product_id': 'product_id is required for this event_type'})

        if et in ('search', 'chat') and not qt:
            raise serializers.ValidationError({'query_text': 'query_text is required for this event_type'})

        if et in ('view', 'add_to_cart', 'purchase'):
            pt = attrs.get('product_type')
            if pt is None:
                raise serializers.ValidationError({'product_type': 'product_type is required for this event_type'})

        return attrs

    def create(self, validated_data):
        event_id = validated_data.get('event_id')
        if not event_id:
            event_id = f"EVT_{uuid.uuid4().hex[:12].upper()}"

        created_at = validated_data.get('created_at') or timezone.now()

        obj = InteractionEvent.objects.create(
            event_id=event_id,
            user_id=validated_data['user_id'],
            session_id=validated_data.get('session_id') or None,
            event_type=validated_data['event_type'],
            product_id=validated_data.get('product_id'),
            query_text=(validated_data.get('query_text') or None),
            duration_ms=validated_data.get('duration_ms'),
            created_at=created_at,
            page=validated_data.get('page') or None,
            product_type=validated_data.get('product_type') or None,
            metadata=validated_data.get('metadata') or {},
            neo4j_synced=False,
            neo4j_synced_at=None,
            neo4j_error=None,
        )
        return obj
