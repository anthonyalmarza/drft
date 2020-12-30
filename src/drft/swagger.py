from drf_yasg import openapi
from drf_yasg.inspectors import CoreAPICompatInspector


class PaginatorInspector(CoreAPICompatInspector):
    def get_paginated_response(self, paginator, response_schema):
        assert (
            response_schema.type == openapi.TYPE_ARRAY
        ), "array return expected for paged response"
        paged_schema = None
        method = getattr(paginator, "get_swagger_paginated_schema", None)
        if method:
            paged_schema = method(response_schema)
        return paged_schema
