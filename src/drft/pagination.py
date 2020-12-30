from collections import OrderedDict

from drf_yasg import openapi
from rest_framework import pagination
from rest_framework.response import Response


class LimitOffsetPagination(pagination.LimitOffsetPagination):

    max_limit: int = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("total", self.count),
                    ("results", data),
                ]
            )
        )

    @staticmethod
    def get_swagger_paginated_schema(results_schema):
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
                    ("total", openapi.Schema(type=openapi.TYPE_INTEGER)),
                    ("results", results_schema),
                )
            ),
            required=["results", "total"],
        )
