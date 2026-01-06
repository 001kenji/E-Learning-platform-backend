# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'lessons', views.LessonViewSet, basename='lesson')
router.register(r'enrollments', views.CourseEnrollmentViewSet, basename='enrollment')
router.register(r'ratings', views.CourseRatingViewSet, basename='rating')
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional endpoints
    path('courses/<slug:slug>/enroll/', views.CourseViewSet.as_view({'post': 'enroll'})),
    path('courses/<slug:slug>/progress/', views.CourseViewSet.as_view({'get': 'progress'})),
    path('enrollments/<uuid:pk>/update-progress/', 
         views.CourseEnrollmentViewSet.as_view({'post': 'update_progress'})),
    path('enrollments/<uuid:pk>/bookmark/', 
         views.CourseEnrollmentViewSet.as_view({'post': 'bookmark'})),
    path('enrollments/<uuid:pk>/add-note/', 
         views.CourseEnrollmentViewSet.as_view({'post': 'add_note'})),
     path('enrollments/<uuid:pk>/reset-progress/', 
         views.CourseEnrollmentViewSet.as_view({'post': 'reset_progress'})),  # Add this
     path('enrollments/<uuid:pk>/unenroll/', 
         views.CourseEnrollmentViewSet.as_view({'delete': 'unenroll'})),
]