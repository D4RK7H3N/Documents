from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    has_seen_onboarding = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_staff_profile(sender, instance, created, **kwargs):
    if created and (instance.is_staff or instance.is_superuser):
        StaffProfile.objects.get_or_create(user=instance)
