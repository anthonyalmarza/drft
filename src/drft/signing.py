# pylint: disable=no-self-use
import base64
import hashlib
import re
import time
from datetime import timedelta
from typing import Callable, Optional, Union

from .secrets import salted_hmac, compare_digest


_UNSAFE_SEP = re.compile(r"^[A-z0-9-_=]*$")


def b64_encode(value: bytes) -> bytes:
    """
    URL safe base 64 encoding of a value
    :param value: bytes
    :return: bytes
    """
    return base64.urlsafe_b64encode(value).strip(b"=")


def b64_decode(value: bytes) -> bytes:
    """
    URL safe base 64 decoding of a value
    :param value: bytes
    :return: bytes
    """
    pad = b"=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


MaxAge = Union[timedelta, int, float]


def is_valid_timestamp(*, timestamp: int, max_age: Optional[MaxAge]):
    """
    :param timestamp: int seconds since epoch
    :param max_age: Optional timestamp | int | float time in seconds
    :return: bool
    """
    if max_age is None:
        return True
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()
    delta = abs(int(time.time()) - timestamp)
    return delta < max_age


class BadToken(Exception):
    """Signature could not be parsed."""

    def __init__(self, message: str, *, token: str):
        """
        :param message: str Error message
        :param token: str Token attempted to be parse
        """
        super().__init__()
        self.message = message
        self.token = token


class Signer:
    """
    Usage:
        signer = Signer(key="somesupersecretvalue", salt="validate-email")
        token: str = signer.sign(user_id)
        assert user_id == signer.validate(token, max_age=300)
    """

    def __init__(
        self,
        *,
        key: str,
        sep=".",
        byte_order: Optional[str] = None,
        salt: Optional[str] = None,
        algorithm: Callable = hashlib.sha1,
    ):
        """
        :param key: str Secret key
        :param sep: str Seperator for token parts
        :param byte_order: str big | little
        :param salt: Optional str
        :param algorithm: Hashlib algorithm defuault SHA1
        """
        self.key = key
        self.sep = sep
        self.byte_order = byte_order or "big"
        if _UNSAFE_SEP.match(self.sep):
            raise ValueError(
                "Unsafe Signer separator: %r (cannot be empty or consist of "
                "only A-z0-9-_=)" % sep,
            )
        self.salt = salt or self.default_salt
        self.algorithm = algorithm

    @property
    def default_salt(self):
        """
        Generates the default solt for the signer instance.
        :return: str module path dot class name
        """
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def signature(self, value: str, timestamp: int) -> str:
        """
        :param value: str Value to sign
        :param timestamp: int Seconds since epoch
        :return:
        """
        unsigned_value = f"{value}.{timestamp}"
        return b64_encode(
            salted_hmac(
                self.salt, unsigned_value, self.key, algorithm=self.algorithm
            ).digest()
        ).decode()

    def encode_int(self, value: int) -> bytes:
        """
        :param value: int
        :return: bytes
        """
        return b64_encode(value.to_bytes(8, self.byte_order))

    def decode_int(self, value: bytes) -> int:
        """
        :param value: bytes
        :return: int
        """
        return int.from_bytes(b64_decode(value), self.byte_order)

    @staticmethod
    def encode_value(value: str) -> bytes:
        """
        :param value: str
        :return: bytes
        """
        return b64_encode(value.encode())

    @staticmethod
    def decode_value(value: bytes) -> str:
        """
        :param value: bytes
        :return: str
        """
        return b64_decode(value).decode()

    def sign(self, value: str, timestamp: int = None) -> str:
        """
        Generate the self-contained token that can be securely parsed and
        validated if returned.
        :param value: str Value to sign
        :param timestamp: Optional int - Seconds since epoch default now
        :return: str
        """
        timestamp = timestamp or int(time.time())
        return self.sep.join(
            [
                self.encode_value(value).decode(),
                self.encode_int(timestamp).decode(),
                self.signature(value, timestamp),
            ]
        )

    def validate(
        self,
        token: str,
        *,
        max_age: Optional[MaxAge] = None,
        timestamp_validator: Callable = is_valid_timestamp,
        signature_validator: Callable = compare_digest,
    ) -> str:
        """
        Validate the token and return the value that was originally signed if
        valid.
        :param token: str Token to parse and validate
        :param max_age: Optional Seconds the token is allow to be valid for
        :return: str Value that was orginally signed
        """
        if self.sep not in token:
            raise BadToken("Separator not found in token", token=token)
        try:
            encoded_value, encoded_timestamp, sig = token.split(self.sep)
        except ValueError as exc:
            raise BadToken("Invalid token structure", token=token) from exc
        timestamp = self.decode_int(encoded_timestamp.encode())
        value = self.decode_value(encoded_value.encode())
        if not timestamp_validator(timestamp=timestamp, max_age=max_age):
            raise BadToken("Token has expired", token=token)
        if not signature_validator(sig, self.signature(value, timestamp)):
            raise BadToken("Signatures do not match", token=token)
        return value
