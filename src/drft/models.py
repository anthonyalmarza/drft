# pylint: disable=too-few-public-methods
from django.db import models
from django.utils.translation import gettext as _


class TimestampedModel(models.Model):
    """
    Abstract base class with the fields created and modified both indexed.
    """

    created = models.DateTimeField(
        _("Created"),
        auto_now_add=True,
        editable=False,
        db_index=True,
    )
    modified = models.DateTimeField(
        _("Modified"),
        auto_now=True,
        editable=False,
        db_index=True,
    )

    class Meta:
        """Base Meta."""

        abstract = True
