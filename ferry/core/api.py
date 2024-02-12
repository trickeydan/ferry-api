from http import HTTPStatus

from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI, Swagger, errors
from ninja.security import HttpBearer

from ferry.accounts.api import router as accounts_api
from ferry.accounts.models import APIToken
from ferry.court.api import router as court_api

from .schema import ErrorDetail


class TokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> str | None:
        try:
            api_token = APIToken.objects.filter(is_active=True).get(token=token)
            request.user = api_token.user
            return token
        except APIToken.DoesNotExist:
            return None


api = NinjaAPI(title="Ferry API", auth=TokenAuth(), docs=Swagger(settings={"persistAuthorization": True}))

api.add_router("/users", accounts_api)
api.add_router("/", court_api)


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


urls = api.urls
