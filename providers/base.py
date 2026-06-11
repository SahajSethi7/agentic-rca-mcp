"""Provider interface for swappable RCA model backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from schemas import RCAInput, RCAReport

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class RCAProvider(ABC):
    """Abstract interface every RCA provider must implement."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Name of the model used by the provider."""

    @abstractmethod
    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        """Generate a validated RCA report for the supplied input."""

    def create_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[ResponseModel],
        *,
        max_retries: int | None = None,
    ) -> ResponseModel:
        """Run one structured chat completion against this provider's model.

        Shared by the agent loop (revise) and the validation pass. Relies on
        the Instructor-wrapped ``self.client`` that every concrete provider
        configures in ``__init__``.
        """
        return self.client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.model,
            response_model=response_model,
            max_retries=max_retries if max_retries is not None else self.settings.max_retries,  # type: ignore[attr-defined]
            temperature=0,
            messages=messages,
        )
