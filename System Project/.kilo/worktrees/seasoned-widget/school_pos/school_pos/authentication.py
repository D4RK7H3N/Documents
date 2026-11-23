from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class CaseInsensitiveAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows case-insensitive username login.
    
    Usage:
        - User can login with: gabriel34, Gabriel34, GABRIEL34, etc.
        - All variations will work
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Override authenticate to make username case-insensitive
        """
        try:
            # Use iexact for case-insensitive username lookup
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # If multiple users found, try exact match first
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # If no exact match, return None to prevent security issues
                return None

        # Check password and return user if valid
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
    
    def get_user(self, user_id):
        """
        Get user by ID (standard method)
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None