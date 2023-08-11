from omaslib.src.helpers.datatypes import QName


class PropertyClassSingleton(type):
    """
    The idea for this class came from "https://stackoverflow.com/questions/3615565/python-get-constructor-to-return-an-existing-object-instead-of-a-new-one".
    This class is used to create a singleton of the AppendOnlyLog class.
    """
    def __call__(cls, *, property_class_iri: QName, **kwargs):
        key = f'{property_class_iri}'
        if key not in cls._cache:
            self = cls.__new__(cls, property_class_iri=property_class_iri, **kwargs)
            cls.__init__(self, property_class_iri=property_class_iri, **kwargs)
            cls._cache[key] = self
        return cls._cache[key]

    def __init__(cls, name, bases, attributes):
        super().__init__(name, bases, attributes)
        cls._cache = {}
