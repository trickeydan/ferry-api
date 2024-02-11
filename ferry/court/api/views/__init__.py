from ninja import Router

from . import people

router = Router()

router.add_router("/", people.router)
