from django.shortcuts import redirect

class StaffAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.exempt_paths = [
            '/staff/login/',
            '/staff/register/',
            '/admin/',        # Django admin (includes /admin/login/)
            '/static/',
            '/media/',
            '/api/',          # API endpoints should handle their own auth
        ]

    def __call__(self, request):
        # Check if path is exempt
        path = request.path
        is_exempt = any(path.startswith(exempt) for exempt in self.exempt_paths)
        
        # CRITICAL FIX: Don't redirect if it's a POST to login (form submission)
        if path == '/staff/login/' and request.method == 'POST':
            # Let the login view handle the POST request
            response = self.get_response(request)
            return response
        
        # If not exempt and not authenticated, redirect to staff login
        if not is_exempt and not request.user.is_authenticated:
            # Don't redirect if already on login page
            if path != '/staff/login/':
                return redirect('/staff/login/')
        
        response = self.get_response(request)
        return response