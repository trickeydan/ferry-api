import random
from http import HTTPStatus
from uuid import UUID

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, errors

from ferry.core.exceptions import ConflictError, InternalServerError
from ferry.core.schema import ConfirmationDetail, ErrorDetail
from ferry.court.api.schema import RatificationCreate, RatificationDetail
from ferry.court.models import Accusation, Consequence, Person, Ratification

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


@router.post(
    "/{accusation_id}/ratification",
    response={
        HTTPStatus.OK: RatificationDetail,
        HTTPStatus.CONFLICT: ErrorDetail,
        HTTPStatus.UNPROCESSABLE_ENTITY: ErrorDetail,
        HTTPStatus.INTERNAL_SERVER_ERROR: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Create a ratification for an accusation",
)
def ratification_create(request: HttpRequest, accusation_id: UUID, payload: RatificationCreate) -> Ratification:
    assert request.user.is_authenticated
    accusation = get_object_or_404(Accusation, id=accusation_id)

    if Ratification.objects.filter(accusation=accusation).exists():
        raise ConflictError("Ratification already exists")

    try:
        creator = Person.objects.get(id=payload.created_by)
    except Person.DoesNotExist:
        raise errors.ValidationError(
            [{"loc": "created_by", "detail": f"Unable to find person with ID {payload.created_by}"}]
        ) from None

    try:
        consequence = random.choice(Consequence.objects.filter(is_enabled=True).all())  # noqa: S311
    except IndexError:
        raise InternalServerError("No consequences available to assign") from None

    ratification = Ratification(
        accusation=accusation,
        consequence=consequence,
        created_by=creator,
    )

    try:
        ratification.full_clean()
    except ValidationError as e:
        raise errors.ValidationError([{"loc": k, "detail": v} for k, v in e.message_dict.items()]) from e
    ratification.save()

    return ratification


@router.delete(
    "/{accusation_id}/ratification",
    response={
        HTTPStatus.OK: ConfirmationDetail,
        HTTPStatus.NOT_FOUND: ErrorDetail,
        HTTPStatus.UNAUTHORIZED: ErrorDetail,
    },
    summary="Delete a ratification",
)
def ratification_delete(request: HttpRequest, accusation_id: UUID) -> ConfirmationDetail:
    assert request.user.is_authenticated
    ratification = get_object_or_404(Ratification, accusation_id=accusation_id)

    ratification.delete()
    return ConfirmationDetail()
