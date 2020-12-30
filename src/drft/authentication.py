from django.utils.encoding import smart_text
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


def get_authorization_token(request, bearer="Bearer"):
    """Parse a request for the JWT token.

    :param request:
    :param bearer:
    :return None|str: None if the request should pass through or the token str
    """
    auth = get_authorization_header(request).split()
    if not auth or smart_text(auth[0].lower()) != bearer.lower():
        return None

    if len(auth) == 1:
        msg = _("Invalid Authorization header. No credentials provided.")
        raise AuthenticationFailed(msg, "missing_credentials")
    elif len(auth) > 2:
        msg = _(
            "Invalid Authorization header. Credentials string "
            "should not contain spaces."
        )
        raise AuthenticationFailed(msg, "invalid_header")

    return auth[1]
