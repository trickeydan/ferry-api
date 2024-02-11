from ninja import Router

from . import consequences, people

router = Router()

router.add_router("/consequences", consequences.router)
router.add_router("/people", people.router)
