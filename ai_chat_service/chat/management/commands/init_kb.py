from django.core.management.base import BaseCommand

from chat.services import build_kb_index


class Command(BaseCommand):
    help = 'Index markdown files in knowledge_base into a local FAISS vector store'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Recreate the collection before indexing')

    def handle(self, *args, **options):
        result = build_kb_index(force=options['force'])
        self.stdout.write(self.style.SUCCESS(f"Indexed: {result}"))
