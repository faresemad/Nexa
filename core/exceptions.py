# core/exceptions.py
from rest_framework.views import exception_handler
from core.response import APIResponse


class PlanLimitExceeded(Exception):
    def __init__(self, message="تم تجاوز الحد المسموح به في باقتك"):
        self.message = message
        self.error_code = "PLAN_LIMIT_EXCEEDED"
        super().__init__(self.message)


class FacebookAPIError(Exception):
    def __init__(self, message="Facebook API error"):
        self.message = message
        self.error_code = "FACEBOOK_API_ERROR"
        super().__init__(self.message)


class AIServiceError(Exception):
    def __init__(self, message="AI service error"):
        self.message = message
        self.error_code = "AI_SERVICE_ERROR"
        super().__init__(self.message)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code == 403:
            return APIResponse.error(
                message="ليس لديك صلاحية للقيام بهذا الإجراء",
                error_code="FORBIDDEN",
                status=403,
            )
        elif response.status_code == 404:
            return APIResponse.error(
                message="غير موجود", error_code="NOT_FOUND", status=404
            )
        elif response.status_code == 400:
            return APIResponse.error(
                message="خطأ في البيانات المدخلة",
                error_code="VALIDATION_ERROR",
                status=400,
                data=response.data,
            )

    if isinstance(exc, PlanLimitExceeded):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=403
        )
    elif isinstance(exc, FacebookAPIError):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=502
        )
    elif isinstance(exc, AIServiceError):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=502
        )

    return response  # core/exceptions.py


from rest_framework.views import exception_handler
from core.response import APIResponse


class PlanLimitExceeded(Exception):
    def __init__(self, message="تم تجاوز الحد المسموح به في باقتك"):
        self.message = message
        self.error_code = "PLAN_LIMIT_EXCEEDED"
        super().__init__(self.message)


class FacebookAPIError(Exception):
    def __init__(self, message="Facebook API error"):
        self.message = message
        self.error_code = "FACEBOOK_API_ERROR"
        super().__init__(self.message)


class AIServiceError(Exception):
    def __init__(self, message="AI service error"):
        self.message = message
        self.error_code = "AI_SERVICE_ERROR"
        super().__init__(self.message)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code == 403:
            return APIResponse.error(
                message="ليس لديك صلاحية للقيام بهذا الإجراء",
                error_code="FORBIDDEN",
                status=403,
            )
        elif response.status_code == 404:
            return APIResponse.error(
                message="غير موجود", error_code="NOT_FOUND", status=404
            )
        elif response.status_code == 400:
            return APIResponse.error(
                message="خطأ في البيانات المدخلة",
                error_code="VALIDATION_ERROR",
                status=400,
                data=response.data,
            )

    if isinstance(exc, PlanLimitExceeded):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=403
        )
    elif isinstance(exc, FacebookAPIError):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=502
        )
    elif isinstance(exc, AIServiceError):
        return APIResponse.error(
            message=exc.message, error_code=exc.error_code, status=502
        )

    return response
