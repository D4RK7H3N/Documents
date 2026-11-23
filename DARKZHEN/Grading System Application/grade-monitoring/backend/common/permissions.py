from rest_framework.permissions import BasePermission


class IsReadyUser(BasePermission):
    message = "You must change your password before using the system."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and not user.must_change_password)


class IsAuthenticatedActive(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsAdmin(IsReadyUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_admin


class IsTeacher(IsReadyUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "teacher"


class IsStudent(IsReadyUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "student"


class IsTeacherOrAdmin(IsReadyUser):
    def has_permission(self, request, view):
        user = request.user
        if not super().has_permission(request, view):
            return False
        return bool(user.is_admin or user.role == "teacher")
