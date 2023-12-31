from enum import Enum
from typing import Any, Union
from pystrict import strict

from .xsd_datatypes import XsdDatatypes, XsdValidator
from .omaserror import OmasError


@strict
class QName:
    _value: str

    def __init__(self, value: Union['QName', str]) -> None:
        if type(value) is QName:
            self._value = str(value)
            return
        tmp = value.split(':')
        if len(tmp) != 2:
            raise OmasError(f'Invalid string "{value}" for QName')
        if tmp[0] == 'xml':
            if not XsdValidator.validate(XsdDatatypes.NCName, tmp[1]):
                raise OmasError(f'Invalid string "{value}" for QName')
            self._value = value
        else:
            if not XsdValidator.validate(XsdDatatypes.QName, value):
                raise OmasError(f'Invalid string "{value}" for QName')
            self._value = value

    @classmethod
    def build(cls, prefix: str, fragment: str):
        return cls(f"{prefix}:{fragment}")

    def __len__(self) -> int:
        return len(self._value)

    def __add__(self, other: Any) -> 'QName':
        return QName(self._value + str(other))

    def __iadd__(self, other):
        return QName(self._value + str(other))

    def __repr__(self):
        return f'QName("{self._value}")'

    def __str__(self):
        return self._value

    def __eq__(self, other: Any):
        return self._value == str(other)

    def __ne__(self, other: Any):
        return self._value != str(other)

    def __hash__(self):
        return self._value.__hash__()

    @property
    def prefix(self):
        parts = self._value.split(':')
        return parts[0]

    @property
    def fragment(self):
        parts = self._value.split(':')
        return parts[1]


@strict
class BNode:
    __value: str

    def __init__(self, value: str) -> None:
        self.__value = value

    def __str__(self) -> str:
        return self.__value

    def __repr__(self) -> str:
        return f'BNode("{self.__value}")'

    def __eq__(self, other: Any) -> bool:
        return self.__value == str(other)

    def __ne__(self, other: Any) -> bool:
        return self.__value != str(other)

    def __hash__(self):
        return hash(self.__value)

    @property
    def value(self) -> str:
        return self.__value


@strict
class AnyIRI:
    _value: str
    _append_allowed: bool

    def __init__(self, value: Union['AnyIRI', str]):
        if isinstance(value, AnyIRI):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasError(f'Invalid string "{value}" for anyIRI')
            self._value = value
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __add__(self, other: Any) -> 'AnyIRI':
        return AnyIRI(self._value + str(other))

    def __iadd__(self, other) -> 'AnyIRI':
        return AnyIRI(self._value + str(other))

    def __repr__(self) -> str:
        return f"AnyURI({self._value})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        return self._value == str(other)

    def __ne__(self, other: Any) -> bool:
        return self._value != str(other)

    def __hash__(self) -> int:
        return self._value.__hash__()

    def __len__(self):
        return len(self._value)

    @property
    def append_allowed(self) -> bool:
        return self._append_allowed


class NamespaceIRI(AnyIRI):

    def __init__(self, value: Union['NamespaceIRI', str]):
        super().__init__(value)
        if self._value[-1] != '/' and self._value[-1] != '#':
            raise OmasError("NamespaceIRI must end with '/' or '#'!")


@strict
class NCName:
    _value: str

    def __init__(self, value: Union['NCName', str]):
        if isinstance(value, NCName):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.NCName, value):
                raise OmasError("Invalid string for NCName")
            self._value = value

    def __add__(self, other: Any) -> 'NCName':
        return NCName(self._value + str(other))

    def __iadd__(self, other) -> 'NCName':
        return NCName(self._value + str(other))

    def __repr__(self) -> str:
        return f"NCName({self._value})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        return self._value == str(other)

    def __ne__(self, other: Any) -> bool:
        return self._value != str(other)

    def __hash__(self) -> int:
        return self._value.__hash__()


class Action(Enum):
    CREATE = 'create'  # a new value has been added
    MODIFY = 'modify'  # a complex value (LangString, PropertyRestriction) has been modified
    REPLACE = 'replace'  # an existing value has been replaced by a new value
    DELETE = 'delete'  # an existing value has been deleted
