# pylint: disable=unused-wildcard-import, wildcard-import
"""
drft.filters

The `filters` module is designed to extend the functionality made available via
both DRF filters and the `django-filter` projects.
"""
from django.db.models import F, QuerySet
from django_filters import filters as dj_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet as DjangoFilterSet
from django_filters.rest_framework.filters import *  # noqa
from rest_framework import filters


class FilterBackend(DjangoFilterBackend):
    """
    Usage:
        class UserViewSet(ModelViewSet):
            filter_backends = [
                FilterBackend,
                ...
            ]
    """


class FilterSet(DjangoFilterSet):
    """
    Usage:
        class UsersFilterSet(FilterSet):
            class Meta:
                model = User
                fields = ["created", "username"]

        class UsersViewSet(ModelViewSet):
            filterset_class = UserFilterSet
            ...
    """

    def filter_queryset(self, queryset) -> QuerySet:
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.

        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        # NOTE: We extend the class here from django_filter because the
        # assert statement is unnecessary.
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
        return queryset


def _get_field_names(field: str, aliases: dict):
    """
    Override this method to customize how
    :param field:
    :param aliases:
    :return:
    """
    trimmed = field.lstrip("-")
    alias = aliases.get(trimmed, trimmed)
    return alias.split(",")


class OrderingFilterBackend(
    filters.OrderingFilter
):  # pylint: disable=function-redefined
    """
    OrderingFilterBackend extends rest_framework.filters.OrderingFilter to
    provide a configurable `ordering_aliases` class attribute as well as by
    default sorting nulls last.

    Usage:
        # in settings.py
        REST_FRAMEWORK = {
            "DEFAULT_FILTER_BACKENDS": [
                "drft.filters.OrderingFilterBackend"
            ]
        }

        # in a views.py module
        class PostsViewSet(viewsets.ModelViewSet):
            ordering = ["-id"]  # default ordering
            ordering_fields = ["latest-user", "foo", "created"]
            ordering_aliases = {
                "latest-user": "-user__joined",
                "foo": "date_published,created"
    """

    ORDERING_ALIASES_KEY = "ordering_aliases"
    NULLS_LAST = True

    def get_ordering(self, request, queryset, view):
        """
        Override base behaviour to enable ordering_aliases functionality.
        :param request:
        :param queryset:
        :param view:
        :return: QuerySet
        """
        ordering = super().get_ordering(request, queryset, view)
        # NOTE: ordering can be None
        if ordering:
            return self.parse_ordering_fields(ordering, view)
        return ordering

    def parse_ordering_fields(
        self, ordering, view, get_field_names=_get_field_names
    ):
        """
        Return a list of F objects given an ordering value
        :param ordering: str
        :param view:
        :param get_field_names: Callable that parses the alias values given the
            alias key.
        :return: list of F objects
        """
        aliases = getattr(view, self.ORDERING_ALIASES_KEY, None) or {}
        if isinstance(aliases, (list, tuple)):
            aliases = dict(aliases)
        return [
            self.parse_ordering(field, field_name)
            for field in ordering
            for field_name in get_field_names(field, aliases)
        ]

    def parse_ordering(self, field: str, field_name: str):
        """
        Return an F object given the field and the field name wherein the field
        is the user specified alias and the field name is the table column name

        :param field: str
        :param field_name: str
        :return: django.db.models.F
        """
        trimmed = field_name.lstrip("-")
        if field.startswith("-") and not field_name.startswith("-"):
            return F(trimmed).desc(nulls_last=self.NULLS_LAST)
        return F(trimmed).asc(nulls_last=self.NULLS_LAST)


# pylint: disable=invalid-name
def patched_filter_method_call(filter_method, qs, value):
    """Patch the FilterMethod.__call__ method.

    Provides access to the request in filter field method callable.
    Signature for callable is now:
        queryset: models.QuerySet
        field_name: str
        value: Any
        request: rest_framework.request.Request
    """
    if value in EMPTY_VALUES:
        return qs
    filter_field = filter_method.f
    filterset = filter_field.parent
    return filter_method.method(
        qs, filter_field.field_name, value, request=filterset.request
    )


dj_filters.FilterMethod.__call__ = patched_filter_method_call
