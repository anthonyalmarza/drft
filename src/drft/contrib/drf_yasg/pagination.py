from collections import OrderedDict
from typing import List, Any, Optional

try:
    from drf_yasg import openapi
except ImportError as exc:
    raise ImportError(
        "Missing drf-yasg package. Try pip install drft[yasg]."
    ) from exc

from rest_framework import pagination
from rest_framework.response import Response


class LimitOffsetPagination(pagination.LimitOffsetPagination):
    """
    Limit-offset pagination of data.
    """

    max_limit = 100

    def get_paginated_response(self, data: Optional[List[Any]]):
        """
        :param data: Page of data
        :return: rest_framework.response.Response
        """
        return Response(
            OrderedDict(
                [
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("count", self.count),
                    ("results", data),
                ]
            )
        )

    @staticmethod
    def get_swagger_paginated_schema(results_schema: openapi.Schema):
        """
        :param results_schema: openapi.Schema:
            Schema of the items within the paginated response
        :return: openapi.Schema
        """
        url_prop = openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_URI,
            x_nullable=True,
        )
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                (
                    ("next", url_prop),
                    ("previous", url_prop),
                    ("count", openapi.Schema(type=openapi.TYPE_INTEGER)),
                    ("results", results_schema),
                )
            ),
            required=["results", "count"],
        )
