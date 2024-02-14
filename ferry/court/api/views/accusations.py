from http import HTTPStatus

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from ferry.core.schema import ErrorDetail
from ferry.court.api.schema import AccusationDetail
from ferry.court.models import Accusation

router = Router(tags=["Accusations"])


@router.get(
    "/",
    response={HTTPStatus.OK: list[AccusationDetail], HTTPStatus.UNAUTHORIZED: ErrorDetail},
    summary="Get a list of all accusations",
)
@paginate
def accusation_list(request: HttpRequest) -> QuerySet[Accusation]:
    assert request.user.is_authenticated
    return Accusation.objects.prefetch_related("created_by", "suspect").all()
