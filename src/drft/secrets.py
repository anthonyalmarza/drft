"""
drft.secrets

Provides more semantically relevant names to commonly used functions from the
built-in secrets module.
"""
import hashlib
import hmac
import secrets as _secrets
from typing import Callable


def generate_secret(n_bytes=32):
    """
    Generate a hexidecimal secret.
    :param n_bytes: int Default 32
    :return: str
    """
    return _secrets.token_hex(nbytes=n_bytes)


def generate_token(n_bytes=16):
    """
    Generate a url safe secret token
    :param n_bytes: int Default 16
    :return: str
    """
    return _secrets.token_urlsafe(nbytes=n_bytes)


def salted_hmac(
    salt: str, value: str, key: str, *, algorithm: Callable = hashlib.sha1
) -> hmac.HMAC:
    """
    Generate a salted hmac given a secret key, a variable salt and the value to
    hash.
    :param salt: str
    :param value: str
    :param key: str
    :param algorithm:
    :return: hmac.HMAC
    """
    # We need to generate a derived key from our base key.  We can do this by
    # passing the salt and our base key through a pseudo-random function.
    derived_key: bytes = algorithm(salt.encode() + key.encode()).digest()
    # If len(salt + key) > block size of the hash algorithm, the above
    # line is redundant and could be replaced by derived_key = salt + key,
    # since the hmac module does the same thing for keys longer than the block
    # size. However, we should ensure that we *always* do this.
    return hmac.new(derived_key, msg=value.encode(), digestmod=algorithm)


def compare_digest(value1: str, value2: str):
    """
    Safe way to check if two secrets match from their respective digests.
    :param value1: str
    :param value2: str
    :return: Boolean
    """
    return _secrets.compare_digest(value1.encode(), value2.encode())
