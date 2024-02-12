from http import HTTPStatus
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import ConsequenceDetail, ConsequenceUpdate, DeleteConfirmation
from ferry.court.models import Consequence

router = Router(tags=["Consequences"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[ConsequenceDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all consequences",
)
@paginate
def consequence_list(request: HttpRequest) -> QuerySet[Consequence]:
    assert request.user.is_authenticated
    return Consequence.objects.prefetch_related("created_by").all()


@router.get(
    "/{consequence_id}",
    response={
        HTTPStatus.OK: ConsequenceDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Fetch a consequence",
)
def consequence_detail(request: HttpRequest, consequence_id: UUID) -> Consequence:
    assert request.user.is_authenticated
    return get_object_or_404(Consequence, id=consequence_id)


@router.put(
    "/{consequence_id}",
    response={
        HTTPStatus.OK: ConsequenceDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Update a consequence",
)
def consequence_update(request: HttpRequest, consequence_id: UUID, payload: ConsequenceUpdate) -> Consequence:
    assert request.user.is_authenticated
    consequence = get_object_or_404(Consequence, id=consequence_id)

    # Update the consequence object
    consequence.content = payload.content
    consequence.is_enabled = payload.is_enabled
    try:
        consequence.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    consequence.save()

    return consequence


@router.delete(
    "/{consequence_id}",
    response={
        HTTPStatus.OK: DeleteConfirmation,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Delete a consequence",
)
def consequence_delete(request: HttpRequest, consequence_id: UUID) -> DeleteConfirmation:
    assert request.user.is_authenticated
    consequence = get_object_or_404(Consequence, id=consequence_id)

    consequence.delete()
    return DeleteConfirmation()
