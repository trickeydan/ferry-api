from http import HTTPStatus
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import RatificationDetail
from ferry.court.models import Ratification

router = Router(tags=["Ratifications"])


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
