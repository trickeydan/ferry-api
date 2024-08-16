from rest_framework import routers

from ferry.accounts.api import UserViewset
from ferry.court.api.views import ConsequenceViewset, PersonViewset

router = routers.SimpleRouter()
router.register("consequences", ConsequenceViewset, basename="consequences")
router.register("people", PersonViewset, basename="people")
router.register("users", UserViewset, basename="users")

urls = router.urls
