from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate

from ferry.court.models import Person

from .schema import DeleteConfirmation, PersonDetail, PersonUpdate

router = Router()


@router.get("/people", response=list[PersonDetail], tags=["People"], summary="Get a list of all people")
@paginate
def people_list(request: HttpRequest) -> QuerySet[Person]:
    assert request.user.is_authenticated
    return Person.objects.all()


@router.get(
    "/people/by-discord-id/{discord_id}",
    response=PersonDetail,
    tags=["People"],
    summary="Fetch a person by their Discord ID",
)
def people_detail_by_discord_id(request: HttpRequest, discord_id: int) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, discord_id=discord_id)


@router.get("/people/{person_id}", response=PersonDetail, tags=["People"], summary="Fetch a person")
def people_detail(request: HttpRequest, person_id: UUID) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, id=person_id)


@router.put(
    "/people/{person_id}",
    response=PersonDetail,
    tags=["People"],
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

    return person


@router.delete(
    "/people/{person_id}",
    response=DeleteConfirmation,
    tags=["People"],
    summary="Delete a person",
)
def people_delete(request: HttpRequest, person_id: UUID) -> DeleteConfirmation:
    assert request.user.is_authenticated
    person = get_object_or_404(Person, id=person_id)
    person.delete()

    return DeleteConfirmation()
