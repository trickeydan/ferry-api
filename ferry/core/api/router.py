from rest_framework import routers

from ferry.accounts.api import UserViewset

router = routers.SimpleRouter()
router.register("users", UserViewset, basename="users")

urls = router.urls
