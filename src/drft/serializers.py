from typing import Optional, Any
from django.core.validators import RegexValidator
from django.utils.translation import gettext as _
from rest_framework import serializers


ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 32
ALIAS_REGEX = r"^[A-z0-9-_]*$"


class AliasField(serializers.CharField):
    """
    Validates the pattern and size of a char field so to conform to the
    specified alias constraints.

    Usage:

        class UserSerializer(ModelSerializer):
            alias = AliasField()

            class meta:
                model = settings.AUTH_USER_MODEL
    """

    default_error_messages = {
        "invalid": _("This value does not match the required pattern.")
    }

    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        alias_regex: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        :param min_length: Optional int. Default 3
        :param max_length: Optional int. Default 32
        :param alias_regex: Optional regex string used at validation time
        :param kwargs: additional options
        """
        kwargs["min_length"] = min_length or ALIAS_MIN_LENGTH
        kwargs["max_length"] = max_length or ALIAS_MAX_LENGTH
        super().__init__(**kwargs)
        alias_regex = alias_regex or ALIAS_REGEX
        validator = RegexValidator(
            alias_regex, message=self.error_messages["invalid"]
        )
        self.validators.append(validator)


class ModelSerializer(serializers.ModelSerializer):
    """
    Extends rest_framework.seriarlizers.ModelSerializer.

    Adds serializer.request -> rest_framework.request.Request
    """

    @property
    def request(self):
        """
        Request property indexed from self.context.
        :return: rest_framework.request.Request
        """
        return self.context["request"]


class ReadOnlyModelSerializer(ModelSerializer):
    """
    Ensure the rest_framework.serializers.ModelSerializer is read-only
    """

    def create(self, validated_data):
        """
        POST is not allowed.
        """
        raise RuntimeError(f"{self.__class__.__name__} is read-only.")

    def update(self, instance, validated_data):
        """
        PATCH/PUT are not allowed.
        """
        raise RuntimeError(f"{self.__class__.__name__} is read-only.")
