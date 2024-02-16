from http import HTTPStatus
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate
from ninja_extra.ordering import ordering

from ferry.core.schema import ConfirmationDetail, ErrorDetail
from ferry.court.api.schema import ConsequenceCreate, ConsequenceDetail, ConsequenceUpdate
from ferry.court.models import Consequence, Person

router = Router(tags=["Consequences"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[ConsequenceDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all consequences",
)
@paginate
@ordering(ordering_fields=["content", "created_at", "updated_at"])
def consequence_list(request: HttpRequest) -> QuerySet[Consequence]:
    assert request.user.is_authenticated
    return Consequence.objects.prefetch_related("created_by").all()


@router.post(
    "/",
    response={
        HTTPStatus.OK: ConsequenceDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Create a consequence",
)
def consequence_create(request: HttpRequest, payload: ConsequenceCreate) -> Consequence:
    assert request.user.is_authenticated

    try:
        creator = Person.objects.get(id=payload.created_by)
    except Person.DoesNotExist:
        raise errors.ValidationError(
            [{"loc": "created_by", "detail": f"Unable to find person with ID {payload.created_by}"}]
        ) from None

    consequence = Consequence(
        content=payload.content,
        is_enabled=payload.is_enabled,
        created_by=creator,
    )

    try:
        consequence.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    consequence.save()

    return consequence


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
        HTTPStatus.OK: ConfirmationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Delete a consequence",
)
def consequence_delete(request: HttpRequest, consequence_id: UUID) -> ConfirmationDetail:
    assert request.user.is_authenticated
    consequence = get_object_or_404(Consequence, id=consequence_id)

    consequence.delete()
    return ConfirmationDetail()
