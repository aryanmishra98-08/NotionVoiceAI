from setup_loader_app import logger
import bleach
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict, field_validator, ValidationInfo, SecretStr


class SecureBaseModel(BaseModel):
    """
    A base Pydantic model that includes common validation and sanitization logic,
    using Pydantic V2 features and enhanced security practices.
    - Forbids extra fields.
    - Sanitizes all string inputs strictly (removes all HTML).
    - Relies on Pydantic for type validation.
    - Uses field_validators in child classes for specific checks (like non-empty).
    """
    # Use model_config for configuration like forbidding extra fields
    model_config = ConfigDict(extra='forbid')

    # Use @model_validator(mode='before') to sanitize input before Pydantic's main validation
    @model_validator(mode='before')
    @classmethod
    def sanitize_all_inputs(cls, data: Any) -> Any:
        # Ensure data is a dictionary before proceeding with dict operations
        # Pydantic usually handles this, but explicit check before sanitization is safe
        if not isinstance(data, dict):
            # Allow Pydantic to raise its own more specific error if input isn't dict-like
            return data  # Pass non-dict data through for Pydantic's handling

        # Removed the custom keys_to_validate logic - use @field_validator in child models instead.
        # Removed the call to validate_json_data - rely on Pydantic's type validation.

        # Sanitize all string fields recursively
        try:
            sanitized_values = cls.sanitize_recursively(data)
            return sanitized_values
        except ValueError as e:
            # Log and re-raise sanitization errors
            logger.error(f"Input sanitization failed: {e}")
            raise  # Prevent processing potentially unsafe data

    @staticmethod
    def sanitize_input(value: str) -> str:
        """
        Sanitize the input string strictly, removing all HTML tags and attributes.
        """
        # Strict sanitization: Allow no HTML tags or attributes
        sanitized = bleach.clean(
            value,
            tags=[],         # No tags allowed
            attributes={},   # No attributes allowed
            strip=True       # Remove disallowed tags entirely
        )

        # Removed the post-sanitization regex check as bleach(tags=[], strip=True)
        # should effectively remove script tags.

        return sanitized

    @classmethod
    def sanitize_recursively(cls, data: Any) -> Any:
        """
        Recursively sanitize strings within dictionaries and lists.
        """
        if isinstance(data, str):
            try:
                return cls.sanitize_input(data)
            except ValueError as e:
                # Error already logged in sanitize_all_string_fields if called from there
                # This path might be hit if called directly or on top-level string (unlikely for JSON API)
                logger.error(f"Sanitization error for string value: {e}")
                raise ValueError(
                    "Sanitization failed for a string value") from e
        elif isinstance(data, dict):
            sanitized_dict = {}
            for key, value in data.items():
                # Sanitize keys? Usually not necessary if they come from trusted sources (like code)
                # but could be added if keys can be user-influenced. Assuming keys are safe here.
                # Ensure keys are strings (Pydantic usually enforces this for models)
                if not isinstance(key, str):
                    raise ValueError(
                        f"Invalid non-string key found in dictionary: {key}")
                try:
                    sanitized_dict[key] = cls.sanitize_recursively(value)
                except ValueError as e:
                    # Add field context to the error
                    logger.error(f"Sanitization error in field '{key}': {e}")
                    raise ValueError(
                        f"Sanitization failed for field '{key}'") from e
            return sanitized_dict
        elif isinstance(data, list):
            sanitized_list = []
            for index, item in enumerate(data):
                try:
                    sanitized_list.append(cls.sanitize_recursively(item))
                except ValueError as e:
                    logger.error(
                        f"Sanitization error in list item at index {index}: {e}")
                    raise ValueError(
                        f"Sanitization failed for item in list at index {index}") from e
            return sanitized_list
        else:
            # Keep non-string, non-dict, non-list values as is
            # Pydantic will validate their types later
            return data


def check_not_empty(v: str, info: ValidationInfo) -> str:
    """Reusable validator to ensure a string field is not empty or just whitespace."""
    if not v or not v.strip():
        raise ValueError(
            f'{info.field_name} must not be empty or contain only whitespace')
    return v


class LLMSignInRequest(SecureBaseModel):
    ccaas_call_id: str = Field(
        ..., description="The ccaas call id of the running call", min_length=34, max_length=36)
    user_id: str = Field(
        ..., description="The user id of the service account", max_length=50)
    # Use SecretStr for password security
    user_password: SecretStr = Field(
        ..., description="The password of the service_account", min_length=16, max_length=100)

    # Use field validators instead of keys_to_validate
    @field_validator('user_id', 'ccaas_call_id')
    @classmethod
    def username_not_empty(cls, v: str, info: ValidationInfo):
        return check_not_empty(v, info)

    @field_validator('user_password')
    @classmethod
    def password_not_empty(cls, v: SecretStr, info: ValidationInfo):
        # Access the actual password value securely for validation
        if not v.get_secret_value() or not v.get_secret_value().strip():
            raise ValueError(
                f'{info.field_name} must not be empty or contain only whitespace')
        return v


class CCAASSignInRequest(SecureBaseModel):
    user_id: str = Field(
        ..., description="The user id of the service_account", max_length=50)
    ccaas_call_id: str = Field(
        ..., description="The ccaas call id of the running call", min_length=34, max_length=36)
    caller_id: str = Field(
        ..., description="The user id of the user", max_length=15)
    # Use SecretStr for password security
    user_password: SecretStr = Field(
        ..., description="The password of the service_account", min_length=16, max_length=100)

    # Use field validators instead of keys_to_validate
    @field_validator('user_id', 'ccaas_call_id', 'caller_id')
    @classmethod
    def username_not_empty(cls, v: str, info: ValidationInfo):
        return check_not_empty(v, info)

    @field_validator('user_password')
    @classmethod
    def password_not_empty(cls, v: SecretStr, info: ValidationInfo):
        # Access the actual password value securely for validation
        if not v.get_secret_value() or not v.get_secret_value().strip():
            raise ValueError(
                f'{info.field_name} must not be empty or contain only whitespace')
        return v


class CallRequest(SecureBaseModel):
    ccaas_call_id: str = Field(
        ..., description="The call id of the running call", min_length=34, max_length=36)
    user_id: str = Field(
        ..., description="The user id of the service account",  max_length=50)
    call_type: Literal['to-do-list', 'journaling'] = Field(
        ..., description="The type of the call. Must be 'to-do-list' or 'journaling'"
    )

    @field_validator('ccaas_call_id', 'user_id', 'call_type')
    @classmethod
    def twilio_id_not_empty(cls, v: str, info: ValidationInfo):
        return check_not_empty(v, info)
