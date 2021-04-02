# pylint: disable=no-self-use,too-many-ancestors,no-member
# pylint: disable=unused-argument,too-many-arguments
from typing import Optional, Tuple

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db.models import Func, Q, QuerySet
from django.utils.translation import gettext as _
from rest_framework import exceptions, filters
from rest_framework.request import Request
from rest_framework.settings import api_settings

from drft.filters import OrderingFilterBackend


# NOTE: It may be important that the RelevanceSearchFilter is listed before
# the RelevanceOrderingFilterBackend.
class RelevanceOrderingFilterBackend(OrderingFilterBackend):
    """
    An ordering filter backend that strictly enforces that the search parameter
    was passed in the query params when the relevance field is being sorted on.
    """

    search_param = api_settings.SEARCH_PARAM
    default_relevance_field = "relevance"

    def get_relevance_field(self, view) -> str:
        """
        Return the relevance field specified by the view or use the default
        value "relevance".
        :param view: View being called that can optionally set
            `relevance_field` as a class attribute.
        :return: str
        """
        return getattr(view, "relevance_field", self.default_relevance_field)

    def get_ordering(self, request, queryset, view):
        """
        Extends the default get_ordering functionality by checking that the
        search parameter was sent when relevance is being sorted by.
        :param request:
        :param queryset:
        :param view:
        :return:
        """
        ordering = super().get_ordering(request, queryset, view)
        if ordering:
            # NOTE: the following blocks are only necessary to validate that
            # the search param is provided when sorting by relevance. It may be
            # unnecessary in most cases.
            relevance_field = self.get_relevance_field(view)
            relevance_included = False
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


# NOTE: Requires the TrigramExtension
# https://docs.djangoproject.com/en/3.1/ref/contrib/postgres/indexes/
# https://docs.djangoproject.com/en/3.1/ref/contrib/postgres/operations/#django.contrib.postgres.operations.BtreeGistExtension
class RelevanceSearchFilter(filters.SearchFilter):
    """
    Provides an extensible search filter backend that exposes a relevance
    annotation on the QuerySet for sorting and filtering purposes.

    Usage:

        class UsersViewSet(ModelViewSet):
            filter_backends = [
                RelevanceSearchFilter,
                ...
            ]
            similarity_field = "name"
            search_vector = SearchVector("name", weight="A") + \
                SearchVector("username", weight="B")
            search_type = "websearch"
            min_relevance = 0.0
            relevance_field = "relevance"
            serializer_class = UserSerializer

            def get_queryset(self):
                return User.objects.filter(...)
    """

    default_similarity_field = None
    default_search_vector = None
    default_search_type = "plain"
    default_min_relevance = 0.3
    default_max_relevance = None
    default_relevance_field = "relevance"
    _similarity_field = None
    _relevance_field = None
    search_description = _("A search phrase.")

    def get_relevance_field(self, view):
        """
        Return the name to associate relevance to through the annotation.
        :param view:
        :return: str
        """
        # NOTE: Each backend is instantiated once per request
        if self._relevance_field is None:
            self._relevance_field = getattr(
                view, "relevance_field", self.default_relevance_field
            )
        return self._relevance_field

    def get_similarity_field(self, view):
        """
        Return the field from the model to run the trigram similarity against.
        :param view: Should have a `similarity_field` class attribute.
        :return: str
        """
        if self._similarity_field is None:
            field_name = getattr(
                view,
                "relevance_similarity_field",
                self.default_similarity_field,
            )
            self._similarity_field = field_name
        return self._similarity_field

    def get_min_relevance(self, phrase: str, view) -> float:
        """
        Return the minimum relevance threshold for results to return.
        :param phrase: str The search term used.
        :param view: Should have a `min_relevance` class attribute.
        :return: float
        """
        threshold = getattr(view, "min_relevance", self.default_min_relevance)
        if not isinstance(threshold, float):
            raise ValueError(
                f"{view.__class__.__name__}.min_relevance should be a float."
            )
        return threshold

    def get_max_relevance(self, phrase: str, view) -> float:
        """
        Return the minimum relevance threshold for results to return.
        :param phrase: str The search term used.
        :param view: Should have a `max_relevance` class attribute.
        :return: float
        """
        limit = getattr(view, "max_relevance", self.default_max_relevance)
        if not isinstance(limit, float):
            raise ValueError(
                f"{view.__class__.__name__}.max_relevance should be a float."
            )
        return limit

    def get_search_type(self, view) -> str:
        """
        Return the search type to use.
        :param view: Should have a `search_type` class attribute.
        :return: str Default "plain"
        """
        # https://docs.djangoproject.com/en/3.1/ref/contrib/postgres/search/#searchquery
        search_type = getattr(view, "search_type", self.default_search_type)
        if search_type not in SearchQuery.SEARCH_TYPES:
            raise ValueError(
                f"{view.__class__.__name__}.search_type is invalid."
            )
        return search_type

    def get_search_vector(self, queryset: QuerySet, view) -> SearchVector:
        """
        Optionally return a SearchVector object.
        :param queryset:
        :param view: Should have a search_vector attribute.
        :return: SearchVector or None - Default None
        """
        search_vector = getattr(
            view, "relevance_search_vector", self.default_search_vector
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
                    f"{view.__class__.__name__}.relevance_search_vector should"
                    " be an instance of SearchVector"
                )
        return search_vector

    def get_relevance(self, queryset: QuerySet, phrase: str, view) -> Func:
        """
        Return the Django Func to use for the relevance field annotation.
        :param queryset:
        :param phrase: str The search term used.
        :param view:
        :return: Func -> TrigramSimilarity + SearchRank
        """
        similarity_field = self.get_similarity_field(view)
        relevance = TrigramSimilarity(similarity_field, phrase)
        search_vector = self.get_search_vector(queryset, view)
        if search_vector:
            search_type = self.get_search_type(view)
            query = SearchQuery(phrase, search_type=search_type)
            relevance = relevance + SearchRank(search_vector, query)
        return relevance

    def get_relevance_search_params(
        self,
        *,
        phrase: str,
        similarity_field: str,
        relevance_field: str,
        min_relevance: float,
        max_relevance: Optional[float],
        view,
    ) -> Tuple[Tuple, dict]:
        """
        Return a tuple of the filter args and kwargs to use in the search.
        :param phrase: str The search term used
        :param similarity_field: str The field to use in the search query
        :param relevance_field: str The field name to give to the annotation.
        :param min_relevance: float
        :param max_relevance: float or None
        :param view:
        :return: args, kwargs
        """
        relevance_filters = {f"{relevance_field}__gte": min_relevance}
        if max_relevance:
            relevance_filters[f"{relevance_field}__lte"] = max_relevance
        return (
            Q(**relevance_filters)
            | Q(**{f"{similarity_field}__istartswith": phrase}),
        ), {}

    def annotate_relevance(
        self, queryset: QuerySet, phrase: str, view
    ) -> QuerySet:
        """
        Annotate the queryset with the relevance field and SQL function
        :param queryset:
        :param phrase:
        :param view:
        :return:
        """
        relevance = self.get_relevance(queryset, phrase, view)
        relevance_field = self.get_relevance_field(view)
        return queryset.annotate(**{relevance_field: relevance})

    def search(self, queryset: QuerySet, phrase: str, view) -> QuerySet:
        """
        Construct the search given all of the relevance parts.
        :param queryset:
        :param phrase:
        :param view:
        :return: annotated and filtered queryset
        """
        min_relevance = self.get_min_relevance(phrase, view)
        max_relevance = self.get_max_relevance(phrase, view)
        similarity_field = self.get_similarity_field(view)
        relevance_field = self.get_relevance_field(view)
        queryset = self.annotate_relevance(queryset, phrase, view)
        args, kwargs = self.get_relevance_search_params(
            phrase=phrase,
            similarity_field=similarity_field,
            relevance_field=relevance_field,
            min_relevance=min_relevance,
            max_relevance=max_relevance,
            view=view,
        )
        return queryset.filter(*args, **kwargs)

    def filter_queryset(
        self, request: Request, queryset: QuerySet, view
    ) -> QuerySet:
        """
        Overrides the function of the filter so to only enable full-text search
        when the similarity_field and search param are available.
        :param request:
        :param queryset:
        :param view:
        :return: QuerySet
        """
        phrase = request.query_params.get(self.search_param, "")
        similarity_field = self.get_similarity_field(view)
        if phrase and similarity_field:
            return self.search(queryset, phrase, view)
        return super().filter_queryset(request, queryset, view)
