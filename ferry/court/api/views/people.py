from http import HTTPStatus
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import IntegerField, QuerySet, Value
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate

from ferry.core.schema import ConfirmationDetail, ErrorDetail
from ferry.court.api.schema import PersonDetail, PersonUpdate
from ferry.court.models import Person

router = Router(tags=["People"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[PersonDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all people",
)
@paginate
def people_list(request: HttpRequest) -> QuerySet[Person]:
    assert request.user.is_authenticated
    return Person.objects.annotate(current_score=Value(14, output_field=IntegerField())).all()


@router.post(
    "/",
    response={
        HTTPStatus.OK: PersonDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Create a person",
)
def people_create(request: HttpRequest, payload: PersonUpdate) -> Person:
    assert request.user.is_authenticated
    person = Person(
        display_name=payload.display_name,
        discord_id=payload.discord_id,
    )

    try:
        person.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    person.save()

    # HACK
    return Person.objects.annotate(current_score=Value(14, output_field=IntegerField())).get(id=person.id)


@router.get(
    "/by-discord-id/{discord_id}",
    response={
        HTTPStatus.OK: PersonDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Fetch a person by their Discord ID",
)
def people_detail_by_discord_id(request: HttpRequest, discord_id: int) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(
        Person.objects.annotate(current_score=Value(14, output_field=IntegerField())), discord_id=discord_id
    )


@router.get(
    "/{person_id}",
    response={
        HTTPStatus.OK: PersonDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    tags=["People"],
    summary="Fetch a person",
)
def people_detail(request: HttpRequest, person_id: UUID) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(
        Person.objects.annotate(current_score=Value(14, output_field=IntegerField())), id=person_id
    )


@router.put(
    "/{person_id}",
    response={
        HTTPStatus.OK: PersonDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Update a person",
)
def people_update(request: HttpRequest, person_id: UUID, payload: PersonUpdate) -> Person:
    assert request.user.is_authenticated
    person = get_object_or_404(Person, id=person_id)

    # Update the person object
    person.display_name = payload.display_name
    person.discord_id = payload.discord_id

    try:
        person.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    person.save()

    # HACK
    return Person.objects.annotate(current_score=Value(14, output_field=IntegerField())).get(id=person.id)


@router.delete(
    "/{person_id}",
    response={
        HTTPStatus.OK: ConfirmationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Delete a person",
)
def people_delete(request: HttpRequest, person_id: UUID) -> ConfirmationDetail:
    assert request.user.is_authenticated
    person = get_object_or_404(Person, id=person_id)
    person.delete()

    return ConfirmationDetail()
