from django.contrib.postgres.search import (
    SearchRank,
    SearchQuery,
    TrigramSimilarity,
    SearchVector,
)
from django.db.models import F, Q, QuerySet, Func
from django.utils.translation import gettext as _
from django_filters import filters as dj_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet as DJFilterSet,
)
from django_filters.rest_framework.filters import *  # noqa
from rest_framework import filters, exceptions
from rest_framework.request import Request
from rest_framework.settings import api_settings


class OrderingFilter(filters.OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        # NOTE: ordering can be None
        if ordering:
            return self.parse_ordering_fields(ordering, view)
        return ordering

    def parse_ordering_fields(self, ordering, view):
        aliases = getattr(view, "ordering_aliases", None) or {}
        if isinstance(aliases, (list, tuple)):
            aliases = dict(aliases)
        return [
            self.parse_ordering(field, field_name)
            for field in ordering
            for field_name in self.get_field_names(field, aliases)
        ]

    def get_field_names(self, field: str, aliases: dict):
        trimmed = field.lstrip("-")
        alias = aliases.get(trimmed, trimmed)
        return alias.split(",")

    def parse_ordering(self, field: str, field_name: str):
        trimmed = field_name.lstrip("-")
        if field.startswith("-") and not field_name.startswith("-"):
            return F(trimmed).desc(nulls_last=True)
        return F(trimmed).asc(nulls_last=True)


class RelevanceOrderingFilter(OrderingFilter):

    search_param = api_settings.SEARCH_PARAM
    relevance_field = "relevance"

    def get_relevance_field(self, view):
        return getattr(view, "relevance_field", self.relevance_field)

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        relevance_field = self.get_relevance_field(view)
        relevance_included = False
        if ordering:
            for field in ordering:
                relevance_included |= relevance_field in field.expression.name
                if relevance_included:
                    break
            search_phrase = request.query_params.get(self.search_param, "")
            if relevance_included and not search_phrase:
                raise exceptions.ValidationError(
                    {relevance_field: f"{self.search_param} is required"}
                )
            return ordering


class RelevanceSearchFilter(filters.SearchFilter):

    similarity_field = None
    search_vector = None
    search_type = "plain"
    relevance_threshold = 0.3
    relevance_field = "relevance"
    _similarity_field = None
    _relevance_field = None
    search_description = _("A search phrase.")

    def get_relevance_field(self, view):
        if self._relevance_field is None:
            self._relevance_field = getattr(
                view, "relevance_field", self.relevance_field
            )
        return self._relevance_field

    def get_similarity_field(self, view):
        if self._similarity_field is None:
            field_name = getattr(
                view, "relevance_similarity_field", self.similarity_field
            )
            self._similarity_field = field_name
        return self._similarity_field

    def get_search_type(self, view):
        return getattr(view, "search_type", self.search_type)

    def get_relevance(self, queryset: QuerySet, phrase: str, view) -> Func:
        similarity_field = self.get_similarity_field(view)
        search_type = self.get_search_type(view)
        relevance = TrigramSimilarity(similarity_field, phrase)
        query = SearchQuery(phrase, search_type=search_type)
        search_vector = self.get_search_vector(queryset, view)
        if search_vector:
            relevance = relevance + SearchRank(search_vector, query)
        return relevance

    def search(self, queryset: QuerySet, phrase: str, view) -> QuerySet:
        queryset = self.annotate_relevance(queryset, phrase, view)
        threshold = self.get_relevance_threshold(phrase, view)
        similarity_field = self.get_similarity_field(view)
        relevance_field = self.get_relevance_field(view)
        args = self.get_relevance_search_args(
            phrase,
            similarity_field,
            relevance_field,
            threshold,
            view,
        )
        kwargs = self.get_relevance_search_kwargs(
            phrase,
            similarity_field,
            relevance_field,
            threshold,
            view,
        )
        return queryset.filter(*args, **kwargs)

    def get_relevance_threshold(self, phrase: str, view):
        threshold = getattr(
            view, "relevance_threshold", self.relevance_threshold
        )
        if not isinstance(threshold, float):
            raise ValueError("Relevance threshold should be an int.")
        return threshold

    def get_relevance_search_args(
        self,
        phrase: str,
        similarity_field: str,
        relevance_field: str,
        threshold: int,
        view,
    ) -> tuple:
        return (
            Q(**{f"{relevance_field}__gte": threshold})
            | Q(**{f"{similarity_field}__istartswith": phrase}),
        )

    def get_relevance_search_kwargs(
        self,
        phrase: str,
        similarity_field: str,
        relevance_field: str,
        threshold: int,
        view,
    ) -> dict:
        return {}

    def annotate_relevance(
        self, queryset: QuerySet, phrase: str, view
    ) -> QuerySet:
        relevance = self.get_relevance(queryset, phrase, view)
        relevance_field = self.get_relevance_field(view)
        return queryset.annotate(**{relevance_field: relevance})

    def filter_queryset(
        self, request: Request, queryset: QuerySet, view
    ) -> QuerySet:
        phrase = request.query_params.get(self.search_param, "")
        similarity_field = self.get_similarity_field(view)
        if phrase and similarity_field:
            return self.search(queryset, phrase, view)
        return super().filter_queryset(request, queryset, view)

    def get_search_vector(self, queryset: QuerySet, view) -> SearchVector:
        search_vector = getattr(
            view, "relevance_search_vector", self.search_vector
        )
        if search_vector:
            if isinstance(search_vector, (tuple, list)):
                items = search_vector
                name, weight = items[0]
                search_vector = SearchVector(name, weight=weight)
                for name, weight in items[1:]:
                    search_vector += SearchVector(name, weight=weight)
            elif not isinstance(search_vector, SearchVector):
                raise ValueError(
                    "relevance search vector should be an instance of "
                    "SearchVector"
                )
        return search_vector


class FilterBackend(DjangoFilterBackend):
    def get_filterset(self, request, queryset, view):
        filterset_class = self.get_filterset_class(view, queryset)
        if filterset_class is None:
            return None

        kwargs = self.get_filterset_kwargs(request, queryset, view)
        return filterset_class(**kwargs)


class FilterSet(DJFilterSet):
    pass


def patched_call(filter_method, qs, value):
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


dj_filters.FilterMethod.__call__ = patched_call
