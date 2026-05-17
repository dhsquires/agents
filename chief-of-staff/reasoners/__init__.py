from .intake import router as intake_router
from .initiative import router as initiative_router
from .status import router as status_router
from .change import router as change_router
from .knowledge import router as knowledge_router
from .strategy import router as strategy_router
from .persist import router as persist_router
from .respond import router as respond_router
from .slack import router as slack_router

__all__ = [
    "intake_router",
    "initiative_router",
    "status_router",
    "change_router",
    "knowledge_router",
    "strategy_router",
    "persist_router",
    "respond_router",
    "slack_router",
]
