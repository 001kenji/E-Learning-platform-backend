# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from .models import Course, Lesson, CourseEnrollment, UserProgressLog, CourseRating
from .serializers import (
    CourseSerializer, LessonSerializer, CourseEnrollmentSerializer,
    UserProgressLogSerializer, CourseRatingSerializer, ProgressUpdateSerializer
)
from .permissions import IsCourseCreatorOrReadOnly, IsEnrolledOrReadOnly
from rest_framework import serializers
from django.core.exceptions import PermissionDenied
import os
from django.db import models

class CourseViewSet(viewsets.ModelViewSet): 
    """
    ViewSet for managing courses.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCourseCreatorOrReadOnly]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """
        Filter courses based on user permissions and query parameters.
        """
        queryset = Course.objects.all()
        
        # Filter by creator
        creator = self.request.query_params.get('creator', None)
        if creator:
            queryset = queryset.filter(creator__username=creator)
        
        # Filter by public status
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        elif not self.request.user.is_staff:
            # Non-staff users see their own courses and public courses
            queryset = queryset.filter(
                Q(is_public=True) | Q(creator=self.request.user)
            )
        
        # Filter by search term
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Annotate with enrollment status for authenticated users
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_enrolled=Count(
                    'enrollments',
                    filter=Q(enrollments__user=self.request.user)
                )
            )
        
        return queryset.select_related('creator').prefetch_related('lessons')
    
    def perform_create(self, serializer):
        """Set the creator to the current user."""
        serializer.save(creator=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, slug=None):
        """Enroll the current user in the course."""
        course = self.get_object()
        print(request.user, course)
        
        # Check if already enrolled
        if CourseEnrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {'detail': 'Already enrolled in this course.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create enrollment
        enrollment = CourseEnrollment.objects.create(
            user=request.user,
            course=course,
            enrolled_at=timezone.now()
        )
        
        serializer = CourseEnrollmentSerializer(enrollment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def progress(self, request, slug=None):
        """Get current user's progress in this course."""
        course = self.get_object()
        
        try:
            enrollment = CourseEnrollment.objects.get(
                user=request.user,
                course=course
            )
            serializer = CourseEnrollmentSerializer(enrollment, context={'request': request})
            return Response(serializer.data)
        except CourseEnrollment.DoesNotExist:
            return Response(
                {'detail': 'Not enrolled in this course.'},
                status=status.HTTP_404_NOT_FOUND
            )


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing lessons.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsEnrolledOrReadOnly]
    
    def get_queryset(self):
        """Filter lessons based on course permissions."""
        queryset = Lesson.objects.all()
        
        # Filter by course
        course_slug = self.request.query_params.get('course', None)
        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)
            
            # Check course access
            course = get_object_or_404(Course, slug=course_slug)
            if not course.is_public and course.creator != self.request.user:
                if not self.request.user.is_authenticated:
                    raise PermissionDenied
                
                # Check if user is enrolled
                if not CourseEnrollment.objects.filter(
                    user=self.request.user, course=course
                ).exists():
                    raise PermissionDenied
        
        return queryset.select_related('course').order_by('order')
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def next(self, request, pk=None):
        """Get the next lesson."""
        lesson = self.get_object()
        next_lesson = lesson.next_lesson
        
        if next_lesson:
            serializer = self.get_serializer(next_lesson)
            return Response(serializer.data)
        return Response({'detail': 'No more lessons.'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def previous(self, request, pk=None):
        """Get the previous lesson."""
        lesson = self.get_object()
        previous_lesson = lesson.previous_lesson
        
        if previous_lesson:
            serializer = self.get_serializer(previous_lesson)
            return Response(serializer.data)
        return Response({'detail': 'No previous lessons.'}, status=status.HTTP_404_NOT_FOUND)


class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course enrollments.
    """
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own enrollments."""
        return CourseEnrollment.objects.filter(user=self.request.user)\
            .select_related('user', 'course', 'current_lesson')\
            .prefetch_related('course__lessons')
    
    @action(detail=True, methods=['post'])
    def reset_progress(self, request, pk=None):
        """Reset user's progress for this enrollment."""
        enrollment = self.get_object()
        
        # Reset all progress fields
        enrollment.current_page = 1
        enrollment.current_lesson = None
        enrollment.pages_completed = 0
        enrollment.total_pages_viewed = 0
        enrollment.bookmarked_pages = []
        enrollment.notes = {}
        enrollment.completed_at = None
        
        # Clear all progress logs
        UserProgressLog.objects.filter(enrollment=enrollment).delete()
        
        enrollment.save()
        
        # Log the reset action
        UserProgressLog.objects.create(
            enrollment=enrollment,
            page_number=1,
            action='progress_reset',
            metadata={'reset_at': timezone.now().isoformat()}
        )
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'])
    def unenroll(self, request, pk=None):
        """Unenroll user from this course."""
        enrollment = self.get_object()
        
        # Get course to update enrollment count
        course = enrollment.course
        
        # Delete the enrollment
        enrollment_id = enrollment.id
        enrollment.delete()
        
        # Update course enrollment count
        course.total_enrollments = max(0, course.total_enrollments - 1)
        course.save()
        
        return Response(
            {
                'detail': 'Successfully unenrolled from the course.',
                'enrollment_id': str(enrollment_id)
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update progress for a specific enrollment."""
        enrollment = self.get_object()
        serializer = ProgressUpdateSerializer(data=request.data, context={'view': self})
        
        if serializer.is_valid():
            # Update enrollment progress
            page_number = serializer.validated_data['page_number']
            time_spent = serializer.validated_data.get('time_spent', 0)
            action = serializer.validated_data.get('action', 'page_view')
            metadata = serializer.validated_data.get('metadata', {})
            
            # Update enrollment
            enrollment.update_progress(page_number, time_spent)
            
            # Create progress log
            UserProgressLog.objects.create(
                enrollment=enrollment,
                page_number=page_number,
                time_spent=time_spent,
                action=action,
                metadata=metadata
            )
            
            # Return updated enrollment
            serializer = self.get_serializer(enrollment)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """Bookmark a page in the course."""
        enrollment = self.get_object()
        page_number = request.data.get('page_number')
        
        if not page_number:
            return Response(
                {'detail': 'page_number is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if page_number > enrollment.course.total_pages:
            return Response(
                {'detail': 'Page number exceeds course total pages.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add to bookmarks if not already bookmarked
        if page_number not in enrollment.bookmarked_pages:
            enrollment.bookmarked_pages.append(page_number)
            enrollment.save()
            
            # Log the bookmark action
            UserProgressLog.objects.create(
                enrollment=enrollment,
                page_number=page_number,
                action='bookmark',
                metadata={'action': 'added'}
            )
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a page."""
        enrollment = self.get_object()
        page_number = request.data.get('page_number')
        note_text = request.data.get('note')
        
        if not page_number or not note_text:
            return Response(
                {'detail': 'page_number and note are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add or update note
        enrollment.notes[str(page_number)] = note_text
        enrollment.save()
        
        # Log the note action
        UserProgressLog.objects.create(
            enrollment=enrollment,
            page_number=page_number,
            action='note_added',
            metadata={'length': len(note_text)}
        )
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)


class CourseRatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for course ratings and reviews.
    """
    serializer_class = CourseRatingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter ratings by course if provided."""
        queryset = CourseRating.objects.all()
        
        course_slug = self.request.query_params.get('course', None)
        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)
        
        return queryset.select_related('user', 'course')
    
    def perform_create(self, serializer):
        """Check if user has already rated this course."""
        course = serializer.validated_data['course']
        
        if CourseRating.objects.filter(user=self.request.user, course=course).exists():
            raise serializers.ValidationError(
                {'detail': 'You have already rated this course.'}
            )
        
        serializer.save(user=self.request.user)


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for user dashboard statistics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user learning statistics."""
        # Get user's enrollments
        from django.db.models import Sum
        enrollments = CourseEnrollment.objects.filter(user=request.user)
        
        # Calculate statistics
        total_courses = enrollments.count()
        completed_courses = enrollments.filter(completed_at__isnull=False).count()
        in_progress_courses = total_courses - completed_courses
        
        # Calculate total time spent
        total_time_spent = UserProgressLog.objects.filter(
            enrollment__user=request.user
        ).aggregate(total=Sum('time_spent'))['total'] or 0
        
        # Get recent progress
        recent_progress = UserProgressLog.objects.filter(
            enrollment__user=request.user
        ).select_related('enrollment__course').order_by('-created_at')[:10]
        
        # Get courses in progress with progress percentage
        courses_in_progress = enrollments.filter(completed_at__isnull=True)\
            .select_related('course')\
            .annotate(progress_percent=(models.F('pages_completed') * 100) / models.F('course__total_pages'))
        
        return Response({
            'total_courses': total_courses,
            'completed_courses': completed_courses,
            'in_progress_courses': in_progress_courses,
            'total_time_spent_seconds': total_time_spent,
            'total_time_spent_hours': round(total_time_spent / 3600, 1),
            'recent_progress': UserProgressLogSerializer(recent_progress, many=True).data,
            'courses_in_progress': [
                {
                    'course_title': enrollment.course.title,
                    'progress_percent': min(100, enrollment.progress_percentage),
                    'current_page': enrollment.current_page,
                    'total_pages': enrollment.course.total_pages,
                    'course_slug': enrollment.course.slug,
                    'id': enrollment.course.id

                }
                for enrollment in courses_in_progress
            ]
        })