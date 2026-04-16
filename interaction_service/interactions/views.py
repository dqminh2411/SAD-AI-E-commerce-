from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InteractionEvent
from .neo4j_client import upsert_event_to_neo4j
from .serializers import InteractionEventCreateSerializer, InteractionEventSerializer


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({'status': 'ok'})


class EventsView(APIView):
    def get(self, request):
        qs = InteractionEvent.objects.all().order_by('-created_at')

        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        session_id = request.query_params.get('session_id')
        if session_id:
            qs = qs.filter(session_id=session_id)

        event_type = request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        product_id = request.query_params.get('product_id')
        if product_id and str(product_id).isdigit():
            qs = qs.filter(product_id=int(product_id))

        product_type = request.query_params.get('product_type')
        if product_type:
            qs = qs.filter(product_type=product_type)

        limit = request.query_params.get('limit', '200')
        try:
            limit_i = int(limit)
        except Exception:
            limit_i = 200
        limit_i = max(1, min(1000, limit_i))

        data = InteractionEventSerializer(qs[:limit_i], many=True).data
        return Response(data)

    def post(self, request):
        serializer = InteractionEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = serializer.save()
        except IntegrityError:
            return Response({'detail': 'Duplicate event_id'}, status=status.HTTP_409_CONFLICT)

        try:
            upsert_event_to_neo4j(
                event_id=event.event_id,
                user_id=event.user_id,
                session_id=event.session_id,
                event_type=event.event_type,
                product_id=event.product_id,
                query_text=event.query_text,
                created_at_iso=event.created_at.isoformat().replace('+00:00', 'Z'),
                page=event.page,
                product_type=event.product_type,
            )
            event.neo4j_synced = True
            event.neo4j_synced_at = timezone.now()
            event.neo4j_error = None
            event.save(update_fields=['neo4j_synced', 'neo4j_synced_at', 'neo4j_error'])
        except Exception as e:
            event.neo4j_synced = False
            event.neo4j_synced_at = None
            event.neo4j_error = str(e)
            event.save(update_fields=['neo4j_synced', 'neo4j_synced_at', 'neo4j_error'])

        return Response(InteractionEventSerializer(event).data, status=status.HTTP_201_CREATED)
