from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_admin_email_verified(sender, instance, created, **kwargs):
    # Superusers created via CLI should be usable immediately.
    if created and instance.is_superuser and not instance.email_verified:
        User.objects.filter(pk=instance.pk).update(email_verified=True)
