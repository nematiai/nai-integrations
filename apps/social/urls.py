"""Combined social router for NEMI API."""

from ninja import Router

from apps.social.views_accounts import router as accounts_router
from apps.social.views_posting import router as posting_router

router = Router(tags=["Social"])
router.add_router("", accounts_router)
router.add_router("", posting_router)
