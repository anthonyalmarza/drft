import base64
import hashlib
import re
import time
from datetime import timedelta

from .secrets import salted_hmac, compare_digest


_UNSAFE_SEP = re.compile(r"^[A-z0-9-_=]*$")


def b64_encode(s) -> bytes:
    return base64.urlsafe_b64encode(s).strip(b"=")


def b64_decode(s) -> bytes:
    pad = b"=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class BadSignature(Exception):
    """Signature could not be parsed."""

    def __init__(self, message, *, signature):
        self.message = message
        self.signature = signature


class Signer:
    def __init__(
        self,
        *,
        key,
        sep=".",
        byte_order=None,
        salt=None,
        algorithm=hashlib.sha1,
    ):
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
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def signature(self, value, timestamp: int) -> str:
        unsigned_value = f"{value}.{timestamp}"
        return b64_encode(
            salted_hmac(
                self.salt, unsigned_value, self.key, algorithm=self.algorithm
            ).digest()
        ).decode()

    def encode_int(self, value: int) -> bytes:
        return b64_encode(value.to_bytes(8, self.byte_order))

    def decode_int(self, value: bytes) -> int:
        return int.from_bytes(b64_decode(value), self.byte_order)

    def encode_value(self, value):
        return b64_encode(value.encode())

    def decode_value(self, value):
        return b64_decode(value).decode()

    def sign(self, value, timestamp: int = None):
        timestamp = timestamp or int(time.time())
        return self.sep.join(
            [
                self.encode_value(value).decode(),
                self.encode_int(timestamp).decode(),
                self.signature(value, timestamp),
            ]
        )

    def validate(self, signed_value: str, *, max_age=None):
        if self.sep not in signed_value:
            raise BadSignature(
                "Separator not found in value", signature=signed_value
            )
        try:
            encoded_value, encoded_timestamp, sig = signed_value.split(
                self.sep
            )
        except ValueError:
            raise BadSignature(
                "Invalid signature structure", signature=signed_value
            )
        timestamp = self.decode_int(encoded_timestamp.encode())
        value = self.decode_value(encoded_value.encode())
        if max_age and not self.valid_timestamp(timestamp, max_age=max_age):
            raise BadSignature("Signature has expired", signature=signed_value)
        if compare_digest(sig, self.signature(value, timestamp)):
            return value
        raise BadSignature("Signatures do not match", signature=signed_value)

    @staticmethod
    def valid_timestamp(timestamp: int, max_age):
        if isinstance(max_age, timedelta):
            max_age = max_age.total_seconds()
        delta = abs(int(time.time()) - timestamp)
        return delta < max_age
