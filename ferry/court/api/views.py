from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors
from ninja.pagination import paginate

from ferry.court.models import Person

from .schema import PersonDetail, PersonUpdate

router = Router()


@router.get("/people", response=list[PersonDetail], tags=["People"])
@paginate
def people_list(request: HttpRequest) -> QuerySet[Person]:
    assert request.user.is_authenticated
    return Person.objects.all()


@router.get("/people/by-discord-id/{discord_id}", response=PersonDetail, tags=["People"])
def people_detail_by_discord_id(request: HttpRequest, discord_id: int) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, discord_id=discord_id)


@router.get("/people/{person_id}", response=PersonDetail, tags=["People"])
def people_detail(request: HttpRequest, person_id: UUID) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, id=person_id)


@router.put("/people/{person_id}", response=PersonDetail, tags=["People"])
def people_update(request: HttpRequest, person_id: UUID, payload: PersonUpdate) -> Person:
    assert request.user.is_authenticated

    with transaction.atomic():
        person = get_object_or_404(Person.objects.select_for_update(), id=person_id)

        if payload.display_name is not None:
            person.display_name = payload.display_name

        if payload.discord_id is not None:
            if payload.discord_id == 0:
                person.discord_id = None
            else:
                if Person.objects.exclude(id=person.id).filter(discord_id=payload.discord_id).exists():
                    raise errors.HttpError(status_code=400, message="another person has that discord id")
                person.discord_id = payload.discord_id

        # TODO: Check ID
        person.save()
    return person
