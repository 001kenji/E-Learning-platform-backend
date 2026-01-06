from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from .models import User
from .models import Course, Lesson, CourseEnrollment, UserProgressLog, CourseRating
from django.contrib.auth import get_user_model

class UserCreateSerializer(BaseUserCreateSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

User = get_user_model()


# Add bio field to your UserSerializer
class UserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'created_at', 'bio','is_active','is_admin']
        read_only_fields = ['created_at']  # Don't allow updating created_at
    
    def validate_username(self, value):
        """Check if username is already taken (excluding current user)."""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        """Check if email is already in use (excluding current user)."""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email already in use.")
        return value.lower()  # Normalize email to lowercase



class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'slug', 'description', 'page_number', 
                 'page_range', 'estimated_duration', 'order', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    lessons = LessonSerializer(many=True, read_only=True)
    total_duration = serializers.ReadOnlyField()
    is_published = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'creator', 
                 'course_file', 'file_size', 'file_type', 'total_pages',
                 'is_public', 'allow_comments', 'enable_progress_tracking',
                 'created_at', 'updated_at', 'published_at',
                 'total_lessons', 'total_enrollments', 'average_rating',
                 'total_duration', 'is_published', 'lessons','file_url']
        read_only_fields = ['slug', 'file_size', 'file_type', 'total_pages',
                           'created_at', 'updated_at', 'published_at',
                           'total_lessons', 'total_enrollments', 'average_rating']
    
    def get_file_url(self, obj):
            request = self.context.get('request')
            if obj.course_file and hasattr(obj.course_file, 'url'):
                return request.build_absolute_uri(obj.course_file.url)
            return None

    def create(self, validated_data):
        """Set the creator to the current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['creator'] = request.user
        
        # Check file size limit (50MB)
        course_file = validated_data.get('course_file')
        if course_file and course_file.size > 50 * 1024 * 1024:
            raise serializers.ValidationError({
                'course_file': 'File size cannot exceed 50MB.'
            })
        
        return super().create(validated_data)


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    current_lesson = LessonSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    time_spent = serializers.ReadOnlyField()
    notes = serializers.JSONField(default=dict, read_only=True)
    class Meta:
        model = CourseEnrollment
        fields = ['id', 'user', 'course', 'enrolled_at', 'completed_at',
                 'current_page', 'current_lesson', 'pages_completed',
                 'total_pages_viewed', 'last_accessed', 'bookmarked_pages',
                 'notes', 'progress_percentage', 'is_completed', 'time_spent']
        read_only_fields = ['enrolled_at', 'completed_at', 'last_accessed']
    
    def create(self, validated_data):
        """Auto-set user from request."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class UserProgressLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgressLog
        fields = ['id', 'enrollment', 'page_number', 'action', 
                 'time_spent', 'metadata', 'created_at']
        read_only_fields = ['created_at']


class CourseRatingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CourseRating
        fields = ['id', 'user', 'course', 'rating', 'review', 
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        """Auto-set user from request."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class ProgressUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user progress.
    """
    page_number = serializers.IntegerField(min_value=1)
    time_spent = serializers.IntegerField(min_value=0, default=0)
    action = serializers.CharField(max_length=50, default='page_view')
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate(self, data):
        """Validate that page number doesn't exceed course total pages."""
        view = self.context.get('view')
        if view and hasattr(view, 'get_course'):
            course = view.get_course()
            if data['page_number'] > course.total_pages:
                raise serializers.ValidationError({
                    'page_number': f'Page number cannot exceed total pages ({course.total_pages})'
                })
        return data