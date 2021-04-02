from typing import Any, List, Optional, Type

from django.db.models import QuerySet
from rest_framework import (
    decorators,
    mixins,
    response,
    serializers,
    status,
    views,
    viewsets,
)
from rest_framework.settings import api_settings as drf_settings

from drft.filters import FilterSet


def action(
    methods: List[str],
    *,
    detail: bool,
    ordering: Optional[str] = None,
    ordering_fields: Optional[List[str]] = None,
    filterset_class: Optional[Type[FilterSet]] = None,
    **kwargs: Any,
):
    """
    Custom action decorator that wraps rest_framework.decorators.action. Use
    this decorator to reset view class configurations e.g. serializer_class,
    ordering, etc.

    :param methods: List of http methods e.g. ["get", "post"]
    :param detail: Boolean:
        Switch between a detail route (True) and a list route (False).
    :param ordering: Optional list of strings
        Default ordering on the queryset. Default: None
    :param ordering_fields: Optional list of strings.
        List options for ordering. Default: None
    :param filterset_class: Option FilterSet class. Default: None
    :param kwargs: Optional keyword arguments
        e.g. serializer_class, filter_backends, etc.
    :return: Called rest_framework.decorators.action

    Usage:

    from drft.views import action

    class SomeViewSet(...):
        @action(["POST", "GET"], detail=False)
        def some_view(self, request: Request) -> Response:
            ...

        @action(["POST", "GET"], detail=True)
        def some_other_view(
            self,
            request: Request,
            pk: Optional[str] = None
        ) -> Response:
            ...
    """
    defaults = dict(
        detail=detail,
        ordering=ordering,
        ordering_fields=ordering_fields,
        filterset_class=filterset_class,
    )
    defaults.update(kwargs)
    return decorators.action(methods, **defaults)


def paged_response(
    *,
    view: viewsets.GenericViewSet,
    queryset: Optional[QuerySet] = None,
    status_code: Optional[int] = None,
):
    """
    paged_response can be used when there is a need to paginate a custom
    API endpoint.

    Usage:
        class UsersView(ModelViewSet):
            ...

            @action(
                ['get'],
                detail=True,
                serializer_class=PostSerializer,
                filterset_class=PostsFilterSet,
            )
            def posts(self, request: Request, pk: Optional[str] = None):
                queryset = Post.objects.filter(user=self.get_object())
                return paged_response(view=self, queryset=queryset)

    :param view: any instance that statisfies the GenericViewSet interface
    :param queryset: Optional django.db.models.QuerySet.
        Default: get_queryset output
    :param status_code: Optional int
    :return: rest_framework.response.Response
    """
    status_code = status_code or status.HTTP_200_OK
    queryset = queryset or view.get_queryset()
    queryset = view.filter_queryset(queryset)
    page = view.paginate_queryset(queryset)
    if page is not None:
        serializer = view.get_serializer(page, many=True)
        return view.get_paginated_response(serializer.data)

    serializer = view.get_serializer(queryset, many=True)
    return response.Response(serializer.data, status=status_code)


_SENTINAL = object()


class APIView(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    views.APIView,
):  # pylint: disable=too-many-ancestors
    """
    Custom APIView to enable better docs via swagger and make use of the
    available DRF mixins, which should reduce code duplication.

    This class implements the most components of the GenericViewSet interface,
    making it compatible with the drft.views.paged_response utility function.
    """

    serializer_class: Type[serializers.Serializer]
    queryset: Optional[QuerySet] = None
    pagination_class = drf_settings.DEFAULT_PAGINATION_CLASS
    filter_backends = drf_settings.DEFAULT_FILTER_BACKENDS
    _paginator = _SENTINAL

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )

        return self.serializer_class

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            "request": self.request,
            "format": self.format_kwarg,
            "view": self,
        }

    def get_queryset(self) -> QuerySet:
        """
        Override this method to gain more control over how the API behaves in
        response to requests.
        :return: django.db.models.QuerySet
        """
        if self.queryset is None:
            raise ValueError(
                "'%s' should either include a `queryset` attribute, "
                "or override the `get_queryset()` method."
                % self.__class__.__name__
            )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
        return queryset

    def filter_queryset(self, queryset):
        """
        Filter the queryset using the each of the classes listed in
        filter_backends.
        :param queryset: django.db.models.QuerySet
        :return: django.db.models.QuerySet
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @property
    def paginator(self):
        """
        :return: instance of the view pagination class
        """
        if self._paginator is _SENTINAL:
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """

        :param queryset:
        :return:
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self
        )

    def get_paginated_response(self, data):
        """

        :param data:
        :return:
        """
        if self.paginator is None:
            raise ValueError(
                f"{self.__class__.__name__}.pagination_class is None or not "
                "defined."
            )
        return self.paginator.get_paginated_response(data)
