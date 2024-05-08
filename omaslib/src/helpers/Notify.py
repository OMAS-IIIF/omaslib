from enum import Enum
from typing import Callable

from pystrict import strict

from omaslib.src.enums.permissionsetattr import PermissionSetAttr
from omaslib.src.xsd.iri import Iri
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.resourceclassattr import ResourceClassAttribute


@strict
class Notify:
    """
    This class can be used as super-class for a classes used as real (sh:name, sh:description) or
    virtual (Restrictions) props of a PropertyClass. It allows these non-primitive values such
    as of type LangString or PropertyRestriction to notify PropertyClass that something has changed,
    e.g. the change of value
    """
    _notifier: Callable[[PropClassAttr], None]
    _data: Enum

    def __init__(self,
                 notifier: Callable[[PropClassAttr | ResourceClassAttribute | PermissionSetAttr | Iri], None] | None = None,
                 data: PropClassAttr | ResourceClassAttribute | PermissionSetAttr | Iri | None = None):
        """
        Constructor of the notifier. Usually, the notifier is only used a base class and not used directly.
        :param notifier: The callable that is to be called by the subclass when an item is beeing chaged
        :param data: Arbitrary data that will be given to the callback
        """
        self._notifier = notifier
        self._data = data

    def set_notifier(self,
                     notifier: Callable[[Enum | Iri], None],
                     data: Enum | Iri |None = None) -> None:
        """
        Sets the notifier callback function and the data it should return...
        :param notifier: A callable that is to be called by the subclass when an item changes
        :param data: Data to be given to the callback
        :return: None
        """
        self._notifier = notifier
        self._data = data

    def notify(self) -> None:
        """
        Used to call the callback when an item is being modified
        :return: None
        """
        if self._notifier is not None:
            self._notifier(self._data)

