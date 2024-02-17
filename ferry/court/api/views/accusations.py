from http import HTTPStatus
from uuid import UUID

from django.db.models import QuerySet
from django.forms import ValidationError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate
from ninja_extra.ordering import ordering

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import AccusationCreate, AccusationDetail, AccusationUpdate
from ferry.court.models import Accusation, Person

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


@router.post(
    "/",
    response={
        HTTPStatus.OK: AccusationDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Create an accusation",
)
def accusation_create(request: HttpRequest, payload: AccusationCreate) -> Accusation:
    assert request.user.is_authenticated

    error_list = []

    try:
        creator = Person.objects.get(id=payload.created_by)
    except Person.DoesNotExist:
        error_list.append({"loc": "created_by", "detail": f"Unable to find person with ID {payload.created_by}"})

    try:
        suspect = Person.objects.get(id=payload.suspect)
    except Person.DoesNotExist:
        error_list.append({"loc": "suspect", "detail": f"Unable to find person with ID {payload.suspect}"})

    if error_list:
        raise errors.ValidationError(error_list)

    if creator == suspect:
        raise errors.ValidationError(
            [{"loc": "__all__", "detail": "Unable to create accusation that suspects the creator."}]
        )

    accusation = Accusation(
        quote=payload.quote,
        suspect=suspect,
        created_by=creator,
    )

    try:
        accusation.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    accusation.save()

    return accusation


@router.get(
    "/{accusation_id}",
    response={
        HTTPStatus.OK: AccusationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Fetch an accusation",
)
def accusation_detail(request: HttpRequest, accusation_id: UUID) -> Accusation:
    assert request.user.is_authenticated
    return get_object_or_404(Accusation, id=accusation_id)


@router.put(
    "/{accusation_id}",
    response={
        HTTPStatus.OK: AccusationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Update an accusation",
)
def accusation_update(request: HttpRequest, accusation_id: UUID, payload: AccusationUpdate) -> Accusation:
    assert request.user.is_authenticated
    accusation = get_object_or_404(Accusation, id=accusation_id)

    # Update the accusation object
    accusation.quote = payload.quote
    try:
        accusation.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    accusation.save()

    return accusation
