from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Gravity Profile', {'fields': ('display_name', 'total_xp', 'current_level', 'location_privacy_mode')}),
    )
    list_display = ('username', 'email', 'display_name', 'current_level', 'is_staff')
