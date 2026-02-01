"""
Base admin classes for cloud storage integrations.
"""

import logging
from functools import lru_cache

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

logger = logging.getLogger(__name__)

# Try to import Unfold, fall back to standard ModelAdmin
try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


class BaseCloudAuthAdmin(BaseModelAdmin):
    """
    Base admin class for cloud storage authentication models.
    
    Provides common display methods and configurations.
    """

    list_display = (
        'user_link',
        'email',
        'display_name',
        'active_icon',
        'connected_at',
        'updated_at',
    )
    list_filter = ('is_active', 'connected_at')
    search_fields = ('user__username', 'user__email', 'email', 'account_id')
    readonly_fields = ('connected_at', 'updated_at', 'account_id')

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email', 'display_name', 'account_id')
        }),
        ('Token Information', {
            'fields': ('token_type', 'expires_at', 'scopes'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'connected_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def has_add_permission(self, request):
        """Prevent manual addition of tokens."""
        return False

    # =========================================================================
    # Display Methods
    # =========================================================================

    def user_link(self, obj):
        """Generate a clickable link to the user's admin page."""
        if hasattr(obj, 'user') and obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "N/A"
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__username'

    def active_icon(self, obj):
        """Display active status as icon."""
        if obj.is_active:
            return format_html('<span style="color: #10b981; font-size: 16px;">✓</span>')
        return format_html('<span style="color: #ef4444; font-size: 16px;">✗</span>')
    active_icon.short_description = 'Active'
    active_icon.admin_order_field = 'is_active'

    def get_status_badge(self, status, color_map=None):
        """Create colored status badges."""
        default_colors = {
            'active': '#10b981',
            'inactive': '#ef4444',
            'expired': '#6b7280',
            'pending': '#f59e0b',
        }
        colors = color_map or default_colors
        color = colors.get(status.lower() if isinstance(status, str) else status, '#6b7280')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 4px; font-weight: 500; font-size: 11px;">{}</span>',
            color,
            str(status).upper()
        )
