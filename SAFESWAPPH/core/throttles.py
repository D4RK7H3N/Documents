from rest_framework.throttling import AnonRateThrottle


class OTPRateThrottle(AnonRateThrottle):
    scope = 'otp'


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    scope = 'register'
