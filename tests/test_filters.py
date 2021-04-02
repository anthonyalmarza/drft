import pytest
from django.db.models import F, QuerySet
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from drft.filters import (
    FilterBackend,
    FilterSet,
    NumberFilter,
    OrderingFilterBackend,
)


class DummyFilterSet(FilterSet):

    cost = NumberFilter(field_name="cost", method="filter_cost", label="cost")

    def filter_cost(
        self, queryset: QuerySet, field_name: str, value: int, request: Request
    ):
        return queryset.filter(**{field_name: value})


@pytest.fixture()
def view(mocker):
    """
    Fixture to mimic the attributes that would be available on a view.
    :param mocker:
    :return: Mock object with the parameterization you would expect on a view
    """
    view = mocker.Mock()
    view.ordering_aliases = {
        "publisher-est": "publisher__established",
        "recent": "published,-created",
    }
    view.ordering_fields = ["publisher-est", "recent", "created"]
    view.ordering = None
    view.filterset_class = DummyFilterSet
    return view


def test_patched_filter_method_call(mocker, view):
    trace = mocker.Mock()
    backend = FilterBackend()
    req = Request(APIRequestFactory().get("/test/?cost=1"))
    queryset = backend.filter_queryset(request=req, queryset=trace, view=view)
    assert queryset == trace.all().filter(**{"cost": 1})


def test_patched_filter_method_call_with_pass_through(mocker, view):
    trace = mocker.Mock()
    backend = FilterBackend()
    req = Request(APIRequestFactory().get("/test/?cost="))
    queryset = backend.filter_queryset(request=req, queryset=trace, view=view)
    assert queryset == trace.all()


def test_ordering_aliases(mocker, view):
    queryset = mocker.Mock()
    backend = OrderingFilterBackend()

    req = Request(APIRequestFactory().get("/test/?sort=publisher-est"))
    ordering = backend.get_ordering(req, queryset, view)
    assert ordering == [F("publisher__established").asc(nulls_last=True)]


def test_ordering_aliases_with_pass_through_sort_value(mocker, view):
    queryset = mocker.Mock()
    backend = OrderingFilterBackend()
    req = Request(APIRequestFactory().get("/test/?sort=created"))
    ordering = backend.get_ordering(req, queryset, view)
    assert ordering == [F("created").asc(nulls_last=True)]


def test_ordering_aliases_with_list_aliases(mocker, view):
    queryset = mocker.Mock()
    backend = OrderingFilterBackend()
    view.ordering_aliases = [
        ("publisher-est", "publisher__established"),
        ("recent", "published,-created"),
    ]
    req = Request(APIRequestFactory().get("/test/?sort=-recent"))
    ordering = backend.get_ordering(req, queryset, view)
    assert ordering == [
        F("published").desc(nulls_last=True),
        F("created").asc(nulls_last=True),
    ]


def test_ordering_aliases_with_no_ordering_parameter(mocker, view):
    queryset = mocker.Mock()
    backend = OrderingFilterBackend()
    req = Request(APIRequestFactory().get("/test/"))
    ordering = backend.get_ordering(req, queryset, view)
    assert ordering is None
