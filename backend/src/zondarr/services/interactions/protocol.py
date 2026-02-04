"""Protocol definition for interaction type handlers.

Defines the InteractionHandler Protocol that all interaction type
implementations must satisfy. Uses structural subtyping — implementations
do not need to inherit from this class.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from zondarr.models.wizard import WizardStep

# Type aliases matching WizardService conventions
ConfigValue = str | int | bool | list[str] | None
StepConfig = dict[str, ConfigValue]
InputConfig = Mapping[str, object]


class InteractionHandler(Protocol):
    """Protocol for wizard step interaction type handlers.

    Each interaction type (click, timer, tos, text_input, quiz) must provide:
    - Config validation: ensures step configuration is valid for the type
    - Response validation: ensures user response satisfies step requirements
    """

    def validate_config(self, config: InputConfig, /) -> StepConfig:
        """Validate step configuration for this interaction type.

        Args:
            config: The raw configuration to validate (positional-only).

        Returns:
            The validated and normalized configuration.

        Raises:
            ValidationError: If the configuration is invalid.
        """
        ...

    def validate_response(
        self,
        step: WizardStep,
        response: InputConfig,
        started_at: datetime | None,
        /,
    ) -> tuple[bool, str | None]:
        """Validate a user's step completion response.

        Args:
            step: The wizard step being validated (positional-only).
            response: The user's response data (positional-only).
            started_at: When the step was started, for timer validation (positional-only).

        Returns:
            A tuple of (is_valid, error_message).
            If valid, error_message is None.
        """
        ...
