from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Only Django superusers may pass.

    IsAdminUser is NOT usable for this: every staff account is created with
    is_staff=True, so it would not separate cashiers from administrators.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class SuperUserDeleteMixin:
    """Money, enrollment and section records may only be deleted by a
    superuser.

    Cashier staff accounts hold is_staff=True, so without this any logged-in
    register could erase sales, payments and student records through the API.
    """

    def get_permissions(self):
        if self.action == "destroy":
            return [IsSuperUser()]
        return super().get_permissions()
