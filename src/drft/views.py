from typing import Type, Optional

from django.db.models import QuerySet
from rest_framework import (
    mixins,
    viewsets,
    views,
    permissions,
    response,
    exceptions,
    decorators,
    serializers,
)
from rest_framework.settings import api_settings as drf_settings


def clean_action(methods, **kwargs):
    defaults = dict(
        detail=True,
        ordering="-created",
        ordering_fields=None,
        filterset_class=None,
    )
    defaults.update(kwargs)
    return decorators.action(methods, **defaults)


class PagedResponseMixin:
    def paged_response(
        self: viewsets.GenericViewSet, queryset: QuerySet = None
    ):
        queryset = queryset or self.get_queryset()
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


class ReadOnlyViewSet(PagedResponseMixin, viewsets.ReadOnlyModelViewSet):

    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ModelViewSet(PagedResponseMixin, viewsets.ModelViewSet):

    permission_classes = [
        permissions.IsAuthenticated,
    ]


class APIView(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    views.APIView,
    PagedResponseMixin,
):
    """Custom APIView to enable better docs via swagger and make use of the
    available DRF mixins."""

    serializer_class: Type[serializers.Serializer]
    queryset: Optional[QuerySet] = None
    pagination_class = drf_settings.DEFAULT_PAGINATION_CLASS
    filter_backends = drf_settings.DEFAULT_FILTER_BACKENDS

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

    def get_queryset(self):
        assert self.queryset is not None, (
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
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self
        )

    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


class SingularResourceAPIView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_object(self):
        queryset = self.get_queryset()
        instance = queryset.first()
        if instance is None:
            raise exceptions.NotFound()
        self.check_object_permissions(self.request, instance)
        return instance

    def get(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return super().update(request, partial=True, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
