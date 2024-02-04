from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate

from ferry.court.models import Person

from .schema import PersonInfo

router = Router()


@router.get("/people", response=list[PersonInfo], tags=["People"])
@paginate
def people_list(request: HttpRequest) -> QuerySet[Person]:
    assert request.user.is_authenticated
    return Person.objects.all()


@router.get("/people/{person_id}", response=PersonInfo, tags=["People"])
def people_detail(request: HttpRequest, person_id: UUID) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, id=person_id)


@router.get("/people/by-discord-id/{discord_id}", response=PersonInfo, tags=["People"])
def people_detail_by_discord_id(request: HttpRequest, discord_id: int) -> Person:
    assert request.user.is_authenticated
    return get_object_or_404(Person, discord_id=discord_id)
