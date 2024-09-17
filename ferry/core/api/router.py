from rest_framework import routers

from ferry.accounts.api import UserViewset
from ferry.court.api.views import AccusationViewset, ConsequenceViewset, PersonViewset
from ferry.pub.api.views import PubEventViewset, PubViewset

router = routers.SimpleRouter()
router.register("court/accusations", AccusationViewset, basename="accusations")
router.register("court/consequences", ConsequenceViewset, basename="consequences")
router.register("pub/events", PubEventViewset, basename="events")
router.register("pub/pubs", PubViewset, basename="pubs")
router.register("people", PersonViewset, basename="people")
router.register("users", UserViewset, basename="users")

urls = router.urls
