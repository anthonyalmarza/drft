# pylint: disable=too-few-public-methods
try:
    from drf_yasg import openapi
    from drf_yasg.inspectors import CoreAPICompatInspector
except ImportError as exc:
    raise ImportError(
        "Missing drf-yasg package. Try pip install drft[yasg]."
    ) from exc


class PaginatorInspector(CoreAPICompatInspector):
    """
    Custom inspector compatible with drft.pagination.LimitOffsetPagination.

    Usasge:
        # in settings.py
        SWAGGER_SETTINGS = {
            "DEFAULT_PAGINATOR_INSPECTORS": [
                "drft.contrib.drf_yasg.swagger.PaginatorInspector"
            ]
        }
    """

    @staticmethod
    def get_paginated_response(paginator, response_schema):
        """
        :param paginator:
        :param response_schema:
        :return: openapi.Schema
        """
        if response_schema.type != openapi.TYPE_ARRAY:
            raise TypeError("array return expected for paged response")
        paged_schema = None
        method = getattr(paginator, "get_swagger_paginated_schema", None)
        if method:
            paged_schema = method(response_schema)
        return paged_schema
