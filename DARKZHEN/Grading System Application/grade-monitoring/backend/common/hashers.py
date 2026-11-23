from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastTestHasher(PBKDF2PasswordHasher):
    iterations = 1
