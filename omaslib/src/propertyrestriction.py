import re
from enum import Enum, unique
from typing import Dict, Union, Set, Optional, Tuple

from pystrict import strict

from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes

@unique
class PropertyRestrictionType(Enum):
    MIN_COUNT = 'sh:minCount'
    MAX_COUNT = 'sh:maxCount'
    LANGUAGE_IN = 'sh:languageIn'
    UNIQUE_LANG = 'sh:uniqueLang'
    MIN_LENGTH = 'sh:minLength'
    MAX_LENGTH = 'sh:maxLength'
    PATTERN = 'sh:pattern'
    MIN_EXCLUSIVE = 'sh:minExclusive'
    MIN_INCLUSIVE = 'sh:minInclusive'
    MAX_EXCLUSIVE = 'sh:maxExclusive'
    MAX_INCLUSIVE = 'sh:maxInclusive'
    LESS_THAN = 'sh:lessThan'
    LESS_THAN_OR_EQUALS = 'sh:lessThanOrEquals'

@unique
class Compare(Enum):
    LT = '__lt__'
    LE = '__le__'
    GT = '__gt__'
    GE = '__ge__'
    XX = '__x__'

@strict
class PropertyRestrictions:
    """
    This class implements the SHACL/OWL restriction that omaslib supports

    SHACl allows to restrict the tha value range of properties. The following restrictions ate
    supported by *omaslib*.

    * cardinality
        - minCount: in OMAS, 0 or 1 is allowed. If omitted, a minCount of 0 is assumed
        - maxCount: in OMAS, 0 or 1 is allowed. If omitted, any number is allowed
    * for strings:
        - languageIn: A set of languages that are allowed for a string property
        - uniqueLang: if "true", each language may occur only once
        - minLength: Minimal length the string must have
        - maxLength: Maximal length that is allowed for the string
        - pattern: A regex expression that the string must fullfill
    * for values that are comparable with "<", ">", ...:
        - minInclusive: The value must be greater-equal than the given value
        - minExclusive: The value must be greater than the given value
        - maxInclusive: Thevalue must be less-equal than the given value
        - maxExclusive: The value must be less than the given value
    * relative comparisons:
        - lessThan: The value must be less that the value of the given property
        - lessThatOrEquals: The value must be less or equal that the one of teh given property

    The class implements the *Dict* semantics: *__len__*, *__getitem__*, *__setitem__* and *__delitem__*
    are implemented as well as the *__str__* method.

    Other methods:

    * shacl(...): Create a trig-formatted fragment to define the restrictions

    """
    _restrictions: Dict[PropertyRestrictionType, Union[bool, int, float, str, Set[Language], QName]]
    _test_in_use: Set[PropertyRestrictionType]
    _changeset: Set[Tuple[PropertyRestrictionType, Action]]

    datatypes = {
        PropertyRestrictionType.MIN_COUNT: {int},
        PropertyRestrictionType.MAX_COUNT: {int},
        PropertyRestrictionType.LANGUAGE_IN: {set},
        PropertyRestrictionType.UNIQUE_LANG: {bool},
        PropertyRestrictionType.MIN_LENGTH: {int},
        PropertyRestrictionType.MAX_LENGTH: {int},
        PropertyRestrictionType.PATTERN: {str},
        PropertyRestrictionType.MIN_EXCLUSIVE: {int, float},
        PropertyRestrictionType.MIN_INCLUSIVE: {int, float},
        PropertyRestrictionType.MAX_EXCLUSIVE: {int, float},
        PropertyRestrictionType.MAX_INCLUSIVE: {int, float},
        PropertyRestrictionType.LESS_THAN: {QName},
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: {QName},
    }
    compare = {
            PropertyRestrictionType.LANGUAGE_IN: Compare.XX,
            PropertyRestrictionType.UNIQUE_LANG: Compare.XX,
            PropertyRestrictionType.MIN_COUNT: Compare.GT,
            PropertyRestrictionType.MAX_COUNT: Compare.LT,
            PropertyRestrictionType.MIN_LENGTH: Compare.GT,
            PropertyRestrictionType.MAX_LENGTH: Compare.LT,
            PropertyRestrictionType.PATTERN: Compare.XX,
            PropertyRestrictionType.MIN_EXCLUSIVE: Compare.GT,
            PropertyRestrictionType.MIN_INCLUSIVE: Compare.GE,
            PropertyRestrictionType.MAX_EXCLUSIVE: Compare.LT,
            PropertyRestrictionType.MAX_INCLUSIVE: Compare.LE,
            PropertyRestrictionType.LESS_THAN: Compare.XX,
            PropertyRestrictionType.LESS_THAN_OR_EQUALS: Compare.XX
        }

    def __init__(self, *,
                 restrictions: Dict[PropertyRestrictionType, Union[bool, int, float, str, Set[Language], QName]] = {}):
        """
        Constructor for restrictions
        :param restrictions: A Dict of restriction. See ~PropertyRestrictionType for SHACL-restriction supported
        """
        for restriction, value in restrictions.items():
            if type(restriction) != PropertyRestrictionType:
                raise OmasError(
                    f'Unsupported restriction "{restriction}"'
                )
            if type(value) not in PropertyRestrictions.datatypes[restriction]:
                raise OmasError(
                    f'Datatype of restriction "{restriction.value}": "{type(value)}" ({value}) is not valid'
                )

        self._restrictions = restrictions
        self._test_in_use = set()
        self._changeset = set()

    def __str__(self) -> str:
        if len(self._restrictions) == 0:
            return ''
        rstr = ' Restrictions: ['
        for name, value in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                rstr += f'{name.value} {{'
                for lang in value:
                    rstr += f' "{lang.name.lower()}"'
                rstr += ' }'
            else:
                rstr += f' {name.value}: {value}'
        rstr += ' ]'
        return rstr

    def __len__(self) -> int:
        return len(self._restrictions)

    def __getitem__(self, restriction_type: PropertyRestrictionType) -> Union[bool, int, float, str, Set[Language], QName]:
        return self._restrictions[restriction_type]

    def __setitem__(self,
                    restriction_type: PropertyRestrictionType,
                    value: Union[bool, int, float, str, Set[Language], QName]):
        if type(restriction_type) != PropertyRestrictionType:
            raise OmasError(
                f'Unsupported restriction "{restriction_type}"'
            )
        if type(value) not in PropertyRestrictions.datatypes[restriction_type]:
            raise OmasError(
                f'Datatype of restriction "{restriction_type.value}": "{type(value)}" ({value}) is not valid'
            )
        if self._restrictions.get(restriction_type):
            if PropertyRestrictions.compare[restriction_type] == Compare.GT:
                if value > self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    self._test_in_use.add(restriction_type)
            elif PropertyRestrictions.compare[restriction_type] == Compare.GE:
                if value >= self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    self._test_in_use.add(restriction_type)
            elif PropertyRestrictions.compare[restriction_type] == Compare.LT:
                if value < self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    self._test_in_use.add(restriction_type)
            elif PropertyRestrictions.compare[restriction_type] == Compare.LE:
                if value <= self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    self._test_in_use.add(restriction_type)
            else:
                self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.REPLACE))
        else:
            self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.CREATE))
        self._restrictions[restriction_type] = value

    def __delitem__(self, restriction_type: PropertyRestrictionType):  # TODO: Sparql output for this case
        if self._restrictions.get(restriction_type) is not None:
            del self._restrictions[restriction_type]
            self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.DELETE))

    @property
    def changeset(self) -> Set[Tuple[PropertyRestrictionType, Action]]:
        return self._changeset

    @property
    def test_in_use(self) -> Set[PropertyRestrictionType]:
        return self._test_in_use

    def get(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Language], QName, None]:
        """
        Get the given restriction
        :param restriction_type: The restriction type
        :return: Value or None
        """
        return self._restrictions.get(restriction_type)

    def clear(self) -> None:
        """
        Clear all restrictions
        :return: None
        """
        for restriction_type in self._restrictions:
            self._changeset.add((restriction_type, Action.DELETE))
        for restriction_type in self._changeset:
            self._restrictions[restriction_type] = None

    def create_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        """
        Return the SHACL fragment for creating the SHACL restrictions

        :param indent: Indent for formatting
        :param indent_inc: Indent increment for formatting
        :return: SHACL fragment string
        """
        blank = ''
        shacl = ''
        for name, rval in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                tmp = [f'"{x.name.lower()}"' for x in rval]
                value = '(' + ' '.join(tmp) + ')'
            elif name == PropertyRestrictionType.UNIQUE_LANG:
                value = 'true' if rval else 'false'
            else:
                value = rval
            shacl += f' ;\n{blank:{indent*indent_inc}}{name.value} {value}'
        return shacl

    def create_owl(self, indent: int = 0, indent_inc: int = 4) -> str:
        """
        Return OWL fragment for creating the ontology of the restrictions
        :param indent: Indent for formatting
        :param indent_inc: Indent increment for formatting
        :return: OWL fragment string
        """
        blank = ''
        sparql = ''
        mincnt = self._restrictions.get(PropertyRestrictionType.MIN_COUNT)
        maxcnt = self._restrictions.get(PropertyRestrictionType.MAX_COUNT)
        if mincnt is not None and maxcnt is not None and mincnt == maxcnt:
            sparql += f' ;\n{blank:{indent*indent_inc}}owl:cardinality {mincnt}'
        else:
            if mincnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:minCardinality {mincnt}'
            if maxcnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:maxCardinality {maxcnt}'
        return sparql

    def update_shacl(self,
                     owlclass_iri: QName,
                     prop_iri: QName,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unittest!
        blank = ''
        sparql_list = []
        for restriction_type, action in self._changeset:
            sparql = ''
            if restriction_type == PropertyRestrictionType.LANGUAGE_IN:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?bnode .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?bnode rdf:rest* ?z .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)
                sparql = ''

            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} {self._restrictions[restriction_type]} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {prop_iri} .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} ?rval\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete_shacl(self,
                     owlclass_iri: QName,
                     prop_iri: QName,
                     restriction_type: PropertyRestrictionType,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unittest!
        blank = ''
        sparql = ''
        if restriction_type == PropertyRestrictionType.LANGUAGE_IN:
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri} .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?bnode .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?bnode rdf:rest* ?z .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}} ;\n'

        sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?rval\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        return sparql

    def delete_owl(self, indent: int = 0, indent_inc: int = 4):
        # TODO: Include into unittest!
        pass



