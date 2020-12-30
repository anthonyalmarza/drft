import hashlib
import hmac
import secrets as _secrets
from typing import Callable


def generate_secret(n_bytes=32):
    return _secrets.token_hex(nbytes=n_bytes)


def generate_token(n_bytes=16):
    return _secrets.token_urlsafe(nbytes=n_bytes)


def salted_hmac(
    salt: str, value: str, key: str, *, algorithm: Callable = hashlib.sha1
):
    # We need to generate a derived key from our base key.  We can do this by
    # passing the salt and our base key through a pseudo-random function.
    derived_key = algorithm(salt.encode() + key.encode()).digest()
    # If len(salt + key) > block size of the hash algorithm, the above
    # line is redundant and could be replaced by derived_key = salt + key,
    # since the hmac module does the same thing for keys longer than the block
    # size. However, we should ensure that we *always* do this.
    return hmac.new(derived_key, msg=value.encode(), digestmod=algorithm)


def compare_digest(value1: str, value2: str):
    return _secrets.compare_digest(value1.encode(), value2.encode())
