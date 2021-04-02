import pytest
from rest_framework.test import APIRequestFactory

from drft.authentication import AuthenticationFailed, get_authorization_token

pytestmark = [pytest.mark.django_db]


def test_no_authorization_header():
    req = APIRequestFactory().get("/foo/", HTTP_FOO="bar")
    token = get_authorization_token(request=req)
    assert token is None


def test_incorrect_authorization_header():
    req = APIRequestFactory().get("/foo/", HTTP_AUTHORIZATION="bearer")
    with pytest.raises(AuthenticationFailed) as exc:
        get_authorization_token(request=req)
    assert exc.value.args[1] == "missing_credentials"


def test_malformed_authorization_header():
    req = APIRequestFactory().get("/foo/", HTTP_AUTHORIZATION="bearer foo bar")
    with pytest.raises(AuthenticationFailed) as exc:
        get_authorization_token(request=req)
    assert exc.value.args[1] == "invalid_header"


def test_get_authorization_token():
    token = "test"
    req = APIRequestFactory().get(
        "/foo/", HTTP_AUTHORIZATION=f"bearer {token}"
    )
    gotten = get_authorization_token(request=req)
    assert gotten.decode() == token
