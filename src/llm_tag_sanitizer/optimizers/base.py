"""Abstract base class for tag optimizers."""

from abc import ABC, abstractmethod

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.tags.models import ProposedChange, TrackInfo
from llm_tag_sanitizer.web_search import WebSearcher


class BaseOptimizer(ABC):
    """Base class for all tag optimization strategies."""

    def __init__(
        self,
        llm_client: OllamaClient,
        web_searcher: WebSearcher | None = None,
    ):
        self.llm_client = llm_client
        self.web_searcher = web_searcher

    @abstractmethod
    def analyze(self, tracks: list[TrackInfo]) -> list[ProposedChange]:
        """Analyze tracks and return proposed changes."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this optimizer."""
        ...
