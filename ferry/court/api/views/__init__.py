from ninja import Router

from . import accusations, consequences, people

router = Router()

router.add_router("/accusations", accusations.router)
router.add_router("/consequences", consequences.router)
router.add_router("/people", people.router)
