# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User
from .models import Course, Lesson, CourseEnrollment, UserProgressLog, CourseRating
from time import timezone
# ========== Custom User Admin ==========
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Custom display - ONLY ONE list_display definition!
    list_display = (
        'username', 
        'email', 
        'full_name',
        'user_type_display',
        'is_active',
        'is_staff',
        'date_joined',
        'bio',
        'user_actions'  # CHANGED: Renamed from 'actions'
    )
    
    list_display_links = ( 'username', 'email')
    
    list_filter = (
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'user_type', 
        'date_joined',
        'created_at'
    )
    
    search_fields = (
        'username', 
        'email', 
        'first_name', 
        'last_name'
    )
    
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)
    
    # CORRECT readonly_fields - only fields that exist in User model
    readonly_fields = (
        'display_id',
        'last_login', 
        'date_joined', 
        'created_at', 
        'updated_at',
        'short_uuid'
    )
    
    
    # Fieldsets for adding new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 
                'email',
                'password1', 
                'password2',
                'first_name', 
                'last_name',
                'user_type'
            ),
        }),
    )
    
    # ========== CUSTOM METHODS ==========
    def get_fieldsets(self, request, obj=None):
        """
        Override to conditionally show password field only when creating new user.
        """
        if obj:  # obj is None when creating a new user
            # Editing existing user - don't show password in fieldsets
            fieldsets = (
                ('Authentication', {
                    'fields': (
                        'display_id',
                        'username', 
                        'email',
                    ),
                    'classes': ('collapse',)
                }),
                
                ('Personal Information', {
                    'fields': (
                        'first_name', 
                        'last_name',
                    ),
                    'classes': ('wide',)
                }),
                
                ('Account Type & Status', {
                    'fields': (
                        'user_type',
                        'is_active',
                        'is_staff', 
                        'is_superuser',
                    ),
                    'classes': ('collapse',)
                }),
                
                ('Permissions', {
                    'fields': (
                        'groups', 
                        'user_permissions'
                    ),
                    'classes': ('collapse',)
                }),
                
                ('Important Dates', {
                    'fields': (
                        'last_login', 
                        'date_joined', 
                        'created_at', 
                        'updated_at'
                    ),
                    'classes': ('collapse',)
                }),
            )
        else:
            # Creating new user - use the fieldsets with password
            fieldsets = (
                ('Authentication', {
                    'fields': (
                        'username', 
                        'email', 
                        'password1',
                        'password2',
                    ),
                    'classes': ('collapse',)
                }),
                
                ('Personal Information', {
                    'fields': (
                        'first_name', 
                        'last_name',
                    ),
                    'classes': ('wide',)
                }),
                
                ('Account Type & Status', {
                    'fields': (
                        'user_type',
                        'is_active',
                        'is_staff', 
                        'is_superuser',
                    ),
                    'classes': ('collapse',)
                }),
            )
        
        return fieldsets
    
    def display_id(self, obj):
        """Display formatted ID with copy button."""
        hex_id = obj.hex_id
        
        # Format as groups of 4 with dashes
        formatted_id = '-'.join([hex_id[i:i+4] for i in range(0, len(hex_id), 4)])
        
        # Add copy button
        copy_button = f"""
        <button class="btn btn-sm btn-outline-secondary" 
                onclick="navigator.clipboard.writeText('{hex_id}')"
                title="Copy to clipboard">
            <i class="fas fa-copy"></i>
        </button>
        """
        
        return mark_safe(f'<code>{formatted_id}</code> {copy_button}')
    display_id.short_description = 'User ID'
    display_id.admin_order_field = 'id'
    
    def full_name(self, obj):
        return obj.get_full_name() or '-'
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'first_name'
    
    def user_type_display(self, obj):
        type_colors = {
            'admin': 'danger',
            'moderator': 'warning',
            'user': 'info'
        }
        color = type_colors.get(obj.user_type, 'secondary')
        return mark_safe(f'<span class="badge badge-{color}">{obj.get_user_type_display()}</span>')
    user_type_display.short_description = 'User Type'
    
    def short_uuid(self, obj):
        """Display short 8-character UUID."""
        return obj.hex_id[:8]
    short_uuid.short_description = 'Short ID'
    
    
    
    
    # ========== CUSTOM ADMIN ACTIONS ==========
    # Rename to avoid conflict with 'actions' method
    admin_actions = ['activate_users', 'deactivate_users', 'make_admin', 'make_regular_user']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            f'{updated} user(s) were successfully activated.',
            messages.SUCCESS
        )
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            f'{updated} user(s) were successfully deactivated.',
            messages.WARNING
        )
    deactivate_users.short_description = "Deactivate selected users"
    
    def make_admin(self, request, queryset):
        updated = queryset.update(user_type='admin', is_staff=True)
        self.message_user(
            request, 
            f'{updated} user(s) were promoted to admin.',
            messages.SUCCESS
        )
    make_admin.short_description = "Make selected users admin"
    
    def make_regular_user(self, request, queryset):
        updated = queryset.update(user_type='user', is_staff=False)
        self.message_user(
            request, 
            f'{updated} user(s) were demoted to regular users.',
            messages.INFO
        )
    make_regular_user.short_description = "Make selected users regular users"
    
    def get_list_display_links(self, request, list_display):
        """Customize which fields are clickable in list view."""
        return ('username', 'email')
    
    def get_queryset(self, request):
        """Custom queryset for different user types."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can't see other superusers
            qs = qs.filter(is_superuser=False)
        return qs
    
    def save_model(self, request, obj, form, change):

        """Auto-set is_staff for admin users."""
        if obj.user_type == 'admin' and not obj.is_staff:
            obj.is_staff = True
        elif obj.user_type != 'admin' and obj.is_staff:
            # Only admins should be staff
            obj.is_staff = False
        super().save_model(request, obj, form, change)

    def user_actions(self, obj):
        """Custom action buttons."""
        view_url = reverse('admin:Authenication_user_change', args=[obj.pk])
        delete_url = reverse('admin:Authenication_user_delete', args=[obj.pk])
        
        return mark_safe(f"""
            <div class="btn-group">
                <a href="{view_url}" class="btn btn-sm btn-info" title="View">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="{delete_url}" class="btn btn-sm btn-danger" title="Delete">
                    <i class="fas fa-trash"></i>
                </a>
            </div>
        """)
    user_actions.short_description = 'Actions'  # Keep display name as 'Actions'
    
    # Admin actions (these are different from list_display methods)
    actions = ['activate_users', 'deactivate_users', 'make_admin', 'make_regular_user']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'is_public', 'total_pages', 'total_lessons', 
                    'total_enrollments', 'average_rating', 'created_at')
    list_filter = ('is_public', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'creator__username', 'creator__email')
    readonly_fields = ('slug', 'file_size', 'file_type', 'total_pages', 
                      'total_lessons', 'total_enrollments', 'average_rating', 
                      'created_at', 'updated_at', 'published_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'creator')
        }),
        ('Course File', {
            'fields': ('course_file', 'file_size', 'file_type', 'total_pages')
        }),
        ('Course Settings', {
            'fields': ('is_public', 'allow_comments', 'enable_progress_tracking')
        }),
        ('Statistics', {
            'fields': ('total_lessons', 'total_enrollments', 'average_rating')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set published_at when making course public."""
        if obj.is_public and not obj.published_at:
            obj.published_at = timezone.now()
        elif not obj.is_public:
            obj.published_at = None
        super().save_model(request, obj, form, change)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'page_number', 'order', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'description', 'course__title')
    ordering = ('course', 'order')
    
    def get_queryset(self, request):
        """Optimize query to select related course."""
        return super().get_queryset(request).select_related('course')


# admin.py
@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress_percentage', 'is_completed', 
                    'last_accessed', 'enrolled_at')
    list_filter = ('enrolled_at', 'last_accessed', 'completed_at')  # Remove 'is_completed'
    search_fields = ('user__username', 'user__email', 'course__title')
    readonly_fields = ('enrolled_at', 'completed_at', 'last_accessed', 
                      'progress_percentage_display')
    
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('user', 'course', 'enrolled_at', 'completed_at')
        }),
        ('Progress Tracking', {
            'fields': ('current_page', 'current_lesson', 'pages_completed', 
                      'total_pages_viewed', 'progress_percentage_display', 'last_accessed')
        }),
        ('User Data', {
            'fields': ('bookmarked_pages', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_percentage_display(self, obj):
        """Display progress as a colored bar."""
        percentage = obj.progress_percentage
        color = 'green' if percentage >= 90 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width:100px; background:#eee; border-radius:3px;">'
            '<div style="width:{}px; height:20px; background-color:{}; '
            'border-radius:3px; text-align:center; color:white; line-height:20px;">'
            '{}%</div></div>',
            percentage, color, round(percentage)
        )
    progress_percentage_display.short_description = 'Progress'
    
    # Optionally, you can add a custom filter for completed status
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'course', 'current_lesson')

@admin.register(UserProgressLog)
class UserProgressLogAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'action', 'page_number', 'time_spent', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('enrollment__user__username', 'enrollment__course__title')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        """Optimize query to select related enrollment, user, and course."""
        return super().get_queryset(request).select_related(
            'enrollment__user', 'enrollment__course'
        )


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'rating', 'created_at', 'updated_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'course__title', 'review')
    readonly_fields = ('created_at', 'updated_at')



    