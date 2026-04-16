from django.core.management.base import BaseCommand
from django.utils import timezone

from interactions.models import InteractionEvent
from interactions.neo4j_client import upsert_event_to_neo4j


class Command(BaseCommand):
    help = 'Sync unsynced interaction events to Neo4j (best-effort, idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1000)

    def handle(self, *args, **options):
        limit = max(1, min(10000, int(options.get('limit') or 1000)))
        qs = InteractionEvent.objects.filter(neo4j_synced=False).order_by('created_at')[:limit]

        total = qs.count()
        ok = 0
        failed = 0

        for ev in qs:
            try:
                upsert_event_to_neo4j(
                    event_id=ev.event_id,
                    user_id=ev.user_id,
                    session_id=ev.session_id,
                    event_type=ev.event_type,
                    product_id=ev.product_id,
                    query_text=ev.query_text,
                    created_at_iso=ev.created_at.isoformat().replace('+00:00', 'Z'),
                    page=ev.page,
                    product_type=ev.product_type,
                )
                ev.neo4j_synced = True
                ev.neo4j_synced_at = timezone.now()
                ev.neo4j_error = None
                ev.save(update_fields=['neo4j_synced', 'neo4j_synced_at', 'neo4j_error'])
                ok += 1
            except Exception as e:
                ev.neo4j_synced = False
                ev.neo4j_synced_at = None
                ev.neo4j_error = str(e)
                ev.save(update_fields=['neo4j_synced', 'neo4j_synced_at', 'neo4j_error'])
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'Sync done. total={total} ok={ok} failed={failed}'))
