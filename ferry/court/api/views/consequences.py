from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from ferry.court.api.schema import ConsequenceDetail
from ferry.court.models import Consequence

router = Router(tags=["Consequences"])


@router.get("/", response=list[ConsequenceDetail], summary="Get a list of all consequences")
@paginate
def consequence_list(request: HttpRequest) -> QuerySet[Consequence]:
    assert request.user.is_authenticated
    return Consequence.objects.prefetch_related("created_by").all()
