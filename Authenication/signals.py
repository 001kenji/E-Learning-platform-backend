# signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Course, Lesson, CourseRating, CourseEnrollment
from django.utils import timezone

@receiver(post_save, sender=Lesson)
def update_course_lesson_count(sender, instance, created, **kwargs):
    """
    Update the total_lessons count for the course when lessons are added/removed.
    """
    if instance.course:
        total_lessons = Lesson.objects.filter(course=instance.course).count()
        Course.objects.filter(id=instance.course.id).update(total_lessons=total_lessons)

@receiver(post_save, sender=CourseRating)
@receiver(post_delete, sender=CourseRating)
def update_course_average_rating(sender, instance, **kwargs):
    """
    Update the average rating for a course when ratings are added/removed.
    """
    if instance.course:
        avg_rating = CourseRating.objects.filter(
            course=instance.course
        ).aggregate(avg=Avg('rating'))['avg'] or 0.0
        
        Course.objects.filter(id=instance.course.id).update(average_rating=avg_rating)

@receiver(post_save, sender=CourseEnrollment)
def update_course_enrollment_count(sender, instance, created, **kwargs):
    """
    Update the total_enrollments count for the course when users enroll.
    """
    if created and instance.course:
        total_enrollments = CourseEnrollment.objects.filter(
            course=instance.course
        ).count()
        
        Course.objects.filter(id=instance.course.id).update(
            total_enrollments=total_enrollments
        )