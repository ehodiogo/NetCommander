from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()

class EnvAuthBackend:
    def authenticate(self, request, username=None, password=None):
        env_user = config("AUTH_USERNAME", default="")
        env_pass = config("AUTH_PASSWORD", default="")

        if username != env_user or password != env_pass:
            return None

        user, created = User.objects.get_or_create(
            username=env_user,
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_unusable_password()
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
