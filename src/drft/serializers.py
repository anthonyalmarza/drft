from django.core.validators import RegexValidator
from django.utils.translation import gettext as _
from rest_framework import serializers

from missives.utils.constants import ALIAS_MAX_LENGTH, ALIAS_MIN_LENGTH

ALIAS_REGEX = r"^[A-z0-9-_]*$"


class AliasField(serializers.CharField):
    default_error_messages = {
        "invalid": _("This value does not match the required pattern.")
    }

    def __init__(self, **kwargs):
        kwargs["max_length"] = ALIAS_MAX_LENGTH
        kwargs["min_length"] = ALIAS_MIN_LENGTH
        super().__init__(**kwargs)
        validator = RegexValidator(
            ALIAS_REGEX, message=self.error_messages["invalid"]
        )
        self.validators.append(validator)


class ModelSerializer(serializers.ModelSerializer):
    """Internal serializer when we need to patch functionality"""

    @property
    def request(self):
        return self.context["request"]


class ReadOnlyModelSerializer(ModelSerializer):
    def create(self, validated_data):
        raise RuntimeError("Read-Only")

    def update(self, instance, validated_data):
        raise RuntimeError("Read-Only")
