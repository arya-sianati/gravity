import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from activities.models import Participation
print(Participation._meta.get_field('joined_at').auto_now_add)
