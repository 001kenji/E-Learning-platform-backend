from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import sanitize_string  # Make sure to create this function

class CustomAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            emailval = sanitize_string(email)
            passwordval = sanitize_string(password)
            user = UserModel.objects.get(email=emailval)
            if user.check_password(passwordval):
                return user
        except UserModel.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

class SetHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        response = self.get_response(request)
        request.META.pop('X-Powered-By', None)
        request.META.pop('Server', None)
        
        #response = self.get_response(request)
        csp_directives = {            
            "frame-ancestors": "'self' http://127.0.0.1:8000 http://localhost:8000 http://localhost:5173" ,
    
        }

        csp_header_value = '; '.join([f"{directive} {value}" for directive, value in csp_directives.items()])
        response['Content-Security-Policy'] = csp_header_value
        

        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'deny'
        return response   