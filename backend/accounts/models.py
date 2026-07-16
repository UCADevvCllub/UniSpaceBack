from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, UserManager


class UserAccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        name = extra_fields.pop('name', '')

        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class UserAccount(AbstractBaseUser, PermissionsMixin):
    email  = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False )
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')],
                            null=True,   blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)

    cohort = models.ForeignKey(
        "camphub.Cohort", on_delete=models.SET_NULL, null=True, blank=True)
    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name

    def __str__(self):
        return self.email
