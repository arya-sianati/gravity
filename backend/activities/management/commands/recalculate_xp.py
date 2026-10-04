from django.core.management.base import BasePageParser, BaseCommand
from django.db.models import Sum
from accounts.models import User
from activities.models import XPTransaction
from activities.logic.xp_service import level_for_xp

class Command(BaseCommand):
    help = 'Recalculate total XP and level for users from their transaction ledger.'

    def handle(self, *args, **options):
        users = User.objects.all()
        fixed = 0
        
        for user in users:
            total = XPTransaction.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
            total = max(0, total)
            correct_lvl = level_for_xp(total)
            
            if user.total_xp != total or user.current_level != correct_lvl:
                user.total_xp = total
                user.current_level = correct_lvl
                user.save(update_fields=['total_xp', 'current_level'])
                fixed += 1
                self.stdout.write(f"Fixed {user.username}: {total} XP, Lvl {correct_lvl}")
                
        self.stdout.write(self.style.SUCCESS(f"Recalculation complete. {fixed} users updated."))
