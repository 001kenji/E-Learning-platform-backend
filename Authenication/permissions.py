# permissions.py
from rest_framework import permissions

class IsCourseCreatorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow course creators to edit their courses.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the course creator
        return obj.creator == request.user


class IsEnrolledOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow enrolled users to access course content.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request for public courses
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'course'):
                return obj.course.is_public or obj.course.creator == request.user
            return True
        
        # Write permissions require enrollment
        if hasattr(obj, 'course'):
            from .models import CourseEnrollment
            return CourseEnrollment.objects.filter(
                user=request.user, course=obj.course
            ).exists()
        
        return False