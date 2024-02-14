from http import HTTPStatus
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import AccusationDetail
from ferry.court.models import Accusation

router = Router(tags=["Accusations"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[AccusationDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all accusations",
)
@paginate
def accusation_list(request: HttpRequest) -> QuerySet[Accusation]:
    assert request.user.is_authenticated
    return Accusation.objects.prefetch_related("created_by", "suspect").all()


@router.get(
    "/{accusation_id}",
    response={
        HTTPStatus.OK: AccusationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Fetch a accusation",
)
def accusation_detail(request: HttpRequest, accusation_id: UUID) -> Accusation:
    assert request.user.is_authenticated
    return get_object_or_404(Accusation, id=accusation_id)
