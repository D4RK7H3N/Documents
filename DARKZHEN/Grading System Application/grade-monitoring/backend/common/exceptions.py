from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

STATUS_CODE_MAP = {
    400: "validation_error",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "throttled",
    500: "server_error",
}


def extract_message(exc):
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        if isinstance(detail.get("detail"), str):
            return detail["detail"]
        if isinstance(detail.get("detail"), list) and detail["detail"]:
            return str(detail["detail"][0])
        for value in detail.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
    if isinstance(detail, list) and detail:
        return str(detail[0])
    return "Request failed."


def error_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        if isinstance(exc, exceptions.APIException):
            response = Response({"error": {"code": "server_error", "message": str(exc)}}, status=500)
        return response
    code = STATUS_CODE_MAP.get(response.status_code, "error")
    message = extract_message(exc)
    payload = {"error": {"code": code, "message": message}}
    detail = getattr(exc, "detail", None)
    if isinstance(detail, (dict, list)):
        payload["error"]["details"] = detail
    response.data = payload
    return response
