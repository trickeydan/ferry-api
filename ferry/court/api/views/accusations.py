from http import HTTPStatus
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja_extra.ordering import ordering

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import AccusationDetail, RatificationDetail
from ferry.court.models import Accusation, Ratification

router = Router(tags=["Accusations"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[AccusationDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all accusations",
)
@paginate
@ordering(ordering_fields=["content", "created_at", "updated_at"])
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


@router.get(
    "/{accusation_id}/ratification",
    response={
        HTTPStatus.OK: RatificationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Fetch the ratification for an accusation, if ratified",
)
def ratification_detail(request: HttpRequest, accusation_id: UUID) -> Ratification:
    assert request.user.is_authenticated
    return get_object_or_404(Ratification, accusation_id=accusation_id)
