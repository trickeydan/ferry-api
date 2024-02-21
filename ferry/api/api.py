from http import HTTPStatus

from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI, Swagger, errors
from ninja.security import HttpBearer

from ferry.accounts.models import APIToken
from ferry.api.routers.accusations import router as accusations_router
from ferry.api.routers.consequences import router as consequences_router
from ferry.api.routers.people import router as people_router
from ferry.api.routers.ratifications import router as ratifications_router
from ferry.api.routers.users import router as users_router
from ferry.core.exceptions import ConflictError, ForbiddenError, InternalServerError

from .schema.core import ErrorDetail


class TokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> str | None:
        try:
            api_token = APIToken.objects.filter(is_active=True).get(token=token)
            request.user = api_token.user
            return token
        except APIToken.DoesNotExist:
            return None


api = NinjaAPI(title="Ferry API", auth=TokenAuth(), docs=Swagger(settings={"persistAuthorization": True}))

api.add_router("/accusations", accusations_router)
api.add_router("/consequences", consequences_router)
api.add_router("/people", people_router)
api.add_router("ratifications", ratifications_router)
api.add_router("/users", users_router)


@api.exception_handler(errors.AuthenticationError)
def authentication_error(request: HttpRequest, exc: errors.AuthenticationError) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Authentication error",
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.UNAUTHORIZED,
    )


@api.exception_handler(ForbiddenError)
def forbidden_error(request: HttpRequest, exc: ForbiddenError) -> HttpResponse:
    error = ErrorDetail(status_code=HTTPStatus.FORBIDDEN, detail=exc.message)
    return api.create_response(
        request,
        error,
        status=HTTPStatus.FORBIDDEN,
    )


@api.exception_handler(errors.ValidationError)
def validation_error(request: HttpRequest, exc: errors.ValidationError) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail=exc.errors,
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
    )


@api.exception_handler(Http404)
def not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.NOT_FOUND,
        detail="Not Found",
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.NOT_FOUND,
    )


@api.exception_handler(ProtectedError)
def protected_error_handler(request: HttpRequest, exc: ProtectedError) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.BAD_REQUEST,
        detail="Unable to delete as referenced by other objects",
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.BAD_REQUEST,
    )


@api.exception_handler(InternalServerError)
def internal_server_error(request: HttpRequest, exc: InternalServerError) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="No consequences available to assign",
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


@api.exception_handler(ConflictError)
def conflict_error(request: HttpRequest, exc: ConflictError) -> HttpResponse:
    error = ErrorDetail(
        status_code=HTTPStatus.CONFLICT,
        detail=exc.message,
    )
    return api.create_response(
        request,
        error,
        status=HTTPStatus.CONFLICT,
    )


urls = api.urls
