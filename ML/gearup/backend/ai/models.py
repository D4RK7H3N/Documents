from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ChatLog(models.Model):
    user = models.ForeignKey(
        User, related_name="chat_logs", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    message = models.TextField()
    response = models.TextField()
    retrieved_product_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "chat logs"

    def __str__(self):
        return f"Chat: {self.message[:50]}"
