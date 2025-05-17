from django.core.management.commands.runserver import Command as BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Runs the server with automatically detected IP address'

    def handle(self, *args, **options):
        if not options.get('addrport'):
            options['addrport'] = f"{settings.LOCAL_IP}:{settings.DEFAULT_PORT}"
            self.stdout.write(f"Starting development server at http://{settings.LOCAL_IP}:{settings.DEFAULT_PORT}/")
        
        # Force IPv4
        options['use_ipv6'] = False
        options['use_reloader'] = True
        
        return super().handle(*args, **options)