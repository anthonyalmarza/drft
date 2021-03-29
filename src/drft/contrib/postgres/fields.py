# pylint: disable=too-few-public-methods
# from django.contrib.postgres.fields import JSONField, ArrayField
# from django.core.exceptions import FieldError
# from django.db.models import Func, Subquery
# from django.utils.translation import gettext as _


# class JsonBuildObject(Func):
#
#     function = "jsonb_build_object"
#     output_field = JSONField()
#
#
# class SubqueryArray(Subquery):
#     template = "ARRAY(%(subquery)s)"
#
#     @property
#     def output_field(self):
#         output_fields = [
#             x.output_field for x in self.get_source_expressions()
#         ]
#
#         if len(output_fields) > 1:
#             raise FieldError("More than one column detected")
#
#         return ArrayField(base_field=output_fields[0])
