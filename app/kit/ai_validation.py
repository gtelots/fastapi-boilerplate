import asyncio
from typing import Literal

import httpx
import structlog
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import app_settings
from app.kit.schemas import Schema
from app.items.models import Item

log = structlog.get_logger(__name__)


class ItemAIValidationVerdict(Schema):
    verdict: Literal["PASS", "FAIL", "UNCERTAIN"] = Field(
        ..., description="PASS | FAIL | UNCERTAIN - indicates compliance status."
    )
    risk_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Risk score from 0 to 100, where 0 is no risk and 100 is high risk.",
    )
    violated_sections: list[str] = Field(
        default_factory=list,
        description="List of violated sections or bullets from the policy.",
    )
    reason: str = Field(
        ...,
        description="A 1 or 3 line explanation of the verdict and the reasoning behind it. The reason will be shown to our customer.",
    )


class ItemAIValidationResult(Schema):
    verdict: ItemAIValidationVerdict = Field(
        description="AI validation verdict"
    )
    timed_out: bool = Field(
        default=False, description="Whether the validation timed out"
    )
    model: str = Field(
        ...,
        description="The model used for validation, e.g. 'gpt-4o-mini'.",
    )


SYSTEM_PROMPT = """

"""

FALLBACK_POLICY = """

"""

TECHNICAL_ERROR_VERDICT = ItemAIValidationVerdict(
    verdict="UNCERTAIN",
    risk_score=50.0,
    violated_sections=[],
    reason="Technical error during validation. Manual review required.",
)

# Cached policy content - will be fetched once and cached
_cached_policy_content: str | None = None


async def _fetch_policy_content() -> str:
    """Fetch and cache the acceptable use policy content."""
    global _cached_policy_content

    if _cached_policy_content is not None:
        return _cached_policy_content

    try:
        # Fetch the actual policy from the documentation URL
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://github.com/gtelots/fastapi-boilerplate/docs/acceptable-use.md",
                timeout=10.0,
                follow_redirects=True,
            )
            if response.status_code == 200:
                _cached_policy_content = response.text
                log.info("Successfully fetched acceptable use policy from docs")
            else:
                log.warning(
                    "Failed to fetch policy, using fallback",
                    status_code=response.status_code,
                )
                _cached_policy_content = FALLBACK_POLICY
    except Exception as e:
        log.warning("Error fetching policy, using fallback", error=str(e))
        _cached_policy_content = FALLBACK_POLICY

    return _cached_policy_content


class ItemAIValidator:
    """AI-powered item details validator using pydantic-ai."""

    def __init__(self) -> None:
        provider = OpenAIProvider(api_key=app_settings.OPENAI_API_KEY)
        self.model = OpenAIChatModel(app_settings.OPENAI_MODEL, provider=provider)

        self.agent = Agent(
            self.model,
            output_type=ItemAIValidationVerdict,
            system_prompt=SYSTEM_PROMPT,
        )

    def _validate_input(self, item: Item) -> None:
        """Validate item input before AI processing."""
        if not item:
            raise ValueError("Item is required")

        if not item.details:
            raise ValueError("Item details are required for AI validation")

        if not item.name:
            raise ValueError("Item name is required")

        # Check details size to prevent excessive API costs
        details_str = str(item.details)
        if len(details_str) > 10000:  # 10KB limit
            raise ValueError("Item details too large for AI validation")

    async def validate_item_details(
        self, item: Item, timeout_seconds: int = 25
    ) -> ItemAIValidationResult:
        """
        Validate item details against acceptable use policy.
        """
        # Validate input first
        self._validate_input(item)

        timed_out = False

        try:
            # Fetch policy content
            policy_content = await _fetch_policy_content()

            # Prepare item context
            org_context = self._prepare_item_context(item)

            # Create the validation prompt
            prompt = f"""
            Analyze this item against our acceptable use policy:

            Item DETAILS:
            {org_context}

            ACCEPTABLE USE POLICY:
            {policy_content}

            Provide your compliance verdict with detailed reasoning.
            """

            # Run AI validation with timeout
            try:
                result = await asyncio.wait_for(
                    self.agent.run(prompt), timeout=timeout_seconds
                )
                verdict = result.output

            except TimeoutError:
                log.warning(
                    "AI validation timed out",
                    item_id=str(item.id),
                    timeout_seconds=timeout_seconds,
                )
                timed_out = True
                verdict = ItemAIValidationVerdict(
                    verdict="UNCERTAIN",
                    risk_score=50.0,
                    violated_sections=[],
                    reason="Validation timed out. Manual review required.",
                )

            return ItemAIValidationResult(
                verdict=verdict, timed_out=timed_out, model=self.model.model_name
            )

        except Exception as e:
            log.error(
                "AI validation failed",
                item_id=str(item.id),
                error=str(e),
            )

            verdict = TECHNICAL_ERROR_VERDICT

            return ItemAIValidationResult(
                verdict=verdict, timed_out=False, model=self.model.model_name
            )

    def _prepare_item_context(self, item: Item) -> str:
        """Prepare item details for AI analysis."""
        details = item.details or {}

        context_parts = [
            f"Item Name: {item.name}",
        ]

        if item.website:
            context_parts.append(f"Website: {item.website}")

        if details.get("about"):
            context_parts.append(f"About: {details['about']}")

        if details.get("product_description"):
            context_parts.append(
                f"Product Description: {details['product_description']}"
            )

        if details.get("intended_use"):
            context_parts.append(f"Intended Use: {details['intended_use']}")

        return "\n".join(context_parts)


validator: ItemAIValidator = ItemAIValidator()
