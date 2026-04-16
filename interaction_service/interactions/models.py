from django.db import models


class InteractionEvent(models.Model):
    event_id = models.CharField(max_length=64, primary_key=True)
    user_id = models.CharField(max_length=64)
    session_id = models.CharField(max_length=128, null=True, blank=True)

    event_type = models.CharField(max_length=32)

    product_id = models.BigIntegerField(null=True, blank=True)
    query_text = models.TextField(null=True, blank=True)
    duration_ms = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField()
    page = models.CharField(max_length=64, null=True, blank=True)
    product_type = models.CharField(max_length=32, null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    neo4j_synced = models.BooleanField(default=False)
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)
    neo4j_error = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'interaction_events'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
