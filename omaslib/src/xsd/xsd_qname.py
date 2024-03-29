from typing import Self, Optional, Any

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_ncname import Xsd_NCName


@strict
@serializer
class Xsd_QName(Xsd):
    """
    # Xsd_QName

    Implements a XSD qualified name (xs:QName) See [W3C documentation](https://www.w3.org/TR/xmlschema-2/#QName).

    A QName consists of a prefix (itelf a NCName) and a fragment (also itself a NCName) seperatet
    by a colon (":").
    The following methods are implemented:

    - *Constructor*: Construct a QName from a QName, string (with a ":") or a prefix/fragment pair
    - *len()*: Return the length of the QName, that is the number of characters of the string representation
    - *repr()*: Return the Python representation of the QName
    - *str()*: Return the string representation of the QName
    - *==*: Test for equality
    - *!=*: Test for inequality
    - *hash()*: Return the hash of the QName
    - *prefix*: Property for the prefix of the QName
    - *fragment*: Property for the fragment of the QName

    """
    _value: str

    def __init__(self, value: Self | str | Xsd_NCName, fragment: Optional[str | Xsd_NCName] = None) -> None:
        """
        Construct a QName from a QName, string (with a ":") or a prefix/fragment pair
        :param value: A Qname, string (with a ":") or a prefix as NCName or string
        :param fragment: A NCName or string (conforming to NCName the convention) for the fragment part
        """
        if fragment is None:
            if isinstance(value, Xsd_QName):
                self._value = str(value)
            elif isinstance(value, str):
                try:
                    prefix, fragment = value.split(':')
                except ValueError as err:
                    raise OmasErrorValue(f'Invalid string "{value}" for QName')
                try:
                    prefix = Xsd_NCName(prefix)
                    fragment = Xsd_NCName(fragment)
                except OmasErrorValue as err:
                    raise OmasErrorValue(f'Invalid string "{value}" for QName. Error: {err}')
                self._value = f'{prefix}:{fragment}'
            else:
                raise OmasErrorValue(f'Invalid value for QName "{value}"')
        else:
            prefix = Xsd_NCName(value)
            fragment = Xsd_NCName(fragment)
            self._value = f'{prefix}:{fragment}'

    def __len__(self) -> int:
        """
        Return the number of characters in the QName
        :return: Length of the QName
        """
        return len(self._value)

    def __add__(self, other: Xsd_NCName | str) -> Self:
        if isinstance(other, Xsd_NCName):
            return Xsd_QName(self._value + other.value)
        else:
            tmp = Xsd_NCName(other)
            return Xsd_QName(self._value + tmp.value)

    def __iadd__(self, other: Xsd_NCName | str) -> Self:
        if isinstance(other, Xsd_NCName):
            self._value += other.value
        else:
            tmp = Xsd_NCName(other)
            self._value += tmp.value
        return self


    def __repr__(self):
        """
        Return the Python representation of the QName
        :return: Python representation of the QName
        """
        return f'Xsd_QName("{self._value}")'

    def __str__(self):
        """
        Return the string representation of the QName
        :return: String representation of the QName
        """
        return self._value

    @property
    def resUri(self) -> str:
        return self._value

    def __eq__(self, other: Any | None) -> bool:
        """
        Test for equality of two QNames
        :param other: Another QName/str to compare with
        :return: True of False
        """
        if other is None:
            return False
        if isinstance(other, str):
            return self._value == other
        return isinstance(other, Xsd_QName) and self._value == other._value

    def __ne__(self, other: Any):
        """
        Test for inequality of two QNames
        :param other: Another QName/str to compare with
        :return: True of False
        """
        if not isinstance(other, Xsd_QName):
            return False
        return self._value != other._value

    def __hash__(self) -> int:
        return hash(self._value)

    @property
    def toRdf(self) -> str:
        return self._value

    def _as_dict(self) -> dict[str, str]:
        return {'value': self._value}

    @property
    def value(self) -> str:
        return self._value

    @property
    def prefix(self) -> str:
        """
        Access the prefix of the QName as property
        :return: Prefix as string
        """
        parts = self._value.split(':')
        return parts[0]

    @property
    def fragment(self) -> str:
        """
        Access the fragment as fragment of the QName as property
        :return: Fragment as string
        """
        parts = self._value.split(':')
        return parts[1]
