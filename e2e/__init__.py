import os

# Playwright's sync API runs an event loop in the test thread, which makes Django refuse ORM calls there as
# "async unsafe". The live server runs in its own thread, so it is safe to allow for browser tests.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
