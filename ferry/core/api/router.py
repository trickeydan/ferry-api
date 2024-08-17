from rest_framework import routers

from ferry.accounts.api import UserViewset
from ferry.court.api.views import AccusationViewset, ConsequenceViewset, PersonViewset

router = routers.SimpleRouter()
router.register("court/accusations", AccusationViewset, basename="accusations")
router.register("court/consequences", ConsequenceViewset, basename="consequences")
router.register("people", PersonViewset, basename="people")
router.register("users", UserViewset, basename="users")

urls = router.urls
