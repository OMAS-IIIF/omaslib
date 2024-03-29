import re
from typing import Self, Type

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_base64Binary(Xsd):

    __value: bytes

    def __init__(self, value: Self | bytes):
        if isinstance(value, Xsd_base64Binary):
            self.__value = value.__value
        elif isinstance(value, bytes):
            self.__value = value
        else:
            OmasErrorValue("Xsd_base64Binary requires bytes parameter")
        if len(value) % 4 != 0:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
        if not bool(re.match(r'^[A-Za-z0-9+/]+={0,2}$', value.decode('utf-8'))):
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
        if not XsdValidator.validate(XsdDatatypes.base64Binary, value.decode('utf-8')):
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')

    def __str__(self):
        return self.__value.decode('utf-8')

    def __repr__(self):
        return f'Xsd_base64Binary(b"{self.__value.decode('utf-8')}")'

    def __eq__(self, other: Self | None) -> bool:
        if other is None:
            return False
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, bytes]:
        return {'value': self.__value}

    @classmethod
    def fromRdf(cls: Type['XsdBase64Binary'], value: str) -> Type['XsdBase64Binary']:
        return cls(value.encode('utf-8'))

    @property
    def toRdf(self) -> str:
        return f'"{self.__value.decode('utf-8')}"^^xsd:base64Binary'

    @property
    def value(self) -> bytes:
        return self.__value

