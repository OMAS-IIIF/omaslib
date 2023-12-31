from typing import Dict, Union, List

from pystrict import strict
from rdflib import Graph
from rdflib.namespace import NamespaceManager, Namespace

from omaslib.src.helpers.datatypes import NCName, AnyIRI, NamespaceIRI, QName
from omaslib.src.helpers.omaserror import OmasError

DEFAULT_CONTEXT = "OMAS_DEFAULT_CONTEXT"

class ContextSingleton(type):
    """
    The idea for this class came from "https://stackoverflow.com/questions/3615565/python-get-constructor-to-return-an-existing-object-instead-of-a-new-one".
    """
    def __call__(cls, *, name, **kwargs):
        if name not in cls._cache:
            self = cls.__new__(cls, name=name, **kwargs)
            cls.__init__(self, name=name, **kwargs)
            cls._cache[name] = self
        return cls._cache[name]

    def __init__(cls, name, bases, attributes):
        super().__init__(name, bases, attributes)
        cls._cache = {}


@strict
class Context(metaclass=ContextSingleton):
    """
    This class is used to hold the "context" of an RDF query/update. The context contains the
    association of the prefixes with the full IRI's of the namespaces.

    The context instances are singletons of the given name. That is, Constructors refering the
    same context name will return a shared context for this name.

    The following methods are defined, In case of an error they raise an OmasError():
    * _[] aka getitem_: Access a full IRI using the prefix, e.g. ```context['rdfs']```
    * _[]_ aka setitem_: Set or modify a prefix/IRI pair, e.g. ```context['test'] = 'http://www.test.org/gaga#'```
    * _del_: Delete an item, e.g. ```del context['skos']```
    * _iri2qname()_: Convert a full IRI to a QNAME ('<prefix>:<name>'), e.g.
      ```context.iri2qname('http://www.w3.org/2000/01/rdf-schema#label')``` -> 'rdfs:label'
    * _qname2iri()_: Convert a qname to a full IRI, e.g.
      ```context.qname2iri('rdfs:label')``` -> 'http://www.w3.org/2000/01/rdf-schema#label'
    * sparql_context: Property that returns the context as sparql compatible string
    * turtle_context: Property that return the context as turtle compatible string
    """
    _name: str
    _context: Dict[NCName, NamespaceIRI]
    _inverse: Dict[NamespaceIRI, NCName]
    _use: List[NCName]

    def __init__(self,
                 name: str):
        """
        Constructs a context with the given name. The following namespaces are defined by default:
        - rdf
        - rdfs
        - owl
        - xsd
        - xml
        - sh (SHACL)
        - skos
        - omas (http://omas.org/base#)
        Note: If a context with the same name already exists, a reference to the already existing is returned:

        :param name: Name of the context
        """
        self._name = name
        self._context = {
            NCName('rdf'): NamespaceIRI('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
            NCName('rdfs'): NamespaceIRI('http://www.w3.org/2000/01/rdf-schema#'),
            NCName('owl'): NamespaceIRI('http://www.w3.org/2002/07/owl#'),
            NCName('xsd'): NamespaceIRI('http://www.w3.org/2001/XMLSchema#'),
            NCName('xml'): NamespaceIRI('http://www.w3.org/XML/1998/namespace#'),
            NCName('sh'): NamespaceIRI('http://www.w3.org/ns/shacl#'),
            NCName('skos'): NamespaceIRI('http://www.w3.org/2004/02/skos/core#'),
            NCName('dc'): NamespaceIRI('http://purl.org/dc/elements/1.1/'),
            NCName('dcterms'): NamespaceIRI('http://purl.org/dc/terms/'),
            NCName('orcid'): NamespaceIRI('https://orcid.org/'),
            NCName('omas'): NamespaceIRI('http://omas.org/base#')
        }
        self._inverse = {
            NamespaceIRI('http://www.w3.org/1999/02/22-rdf-syntax-ns#'): NCName('rdf'),
            NamespaceIRI('http://www.w3.org/2000/01/rdf-schema#'): NCName('rdfs'),
            NamespaceIRI('http://www.w3.org/2002/07/owl#'): NCName('owl'),
            NamespaceIRI('http://www.w3.org/2001/XMLSchema#'): NCName('xsd'),
            NamespaceIRI('http://www.w3.org/XML/1998/namespace#'): NCName('xml'),
            NamespaceIRI('http://www.w3.org/ns/shacl#'): NCName('sh'),
            NamespaceIRI('http://www.w3.org/2004/02/skos/core#'): NCName('skos'),
            NamespaceIRI('http://purl.org/dc/elements/1.1/'): NCName('dc'),
            NamespaceIRI('http://purl.org/dc/terms/'): NCName('dcterms'),
            NamespaceIRI('https://orcid.org/'): NCName('orcid'),
            NamespaceIRI('http://omas.org/base#'): NCName('omas'),
        }
        self._use = []

    def __getitem__(self, prefix: Union[NCName, str]) -> NamespaceIRI:
        """
        Access a context by prefix. The key may be a QName or a valid string

        :param prefix: A valid prefix (QName or string)
        :return: Associated NamespaceIRI
        """
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        try:
            return self._context[prefix]
        except KeyError as err:
            raise OmasError(f'Unknown prefix "{prefix}"')

    def __setitem__(self, prefix: Union[NCName, str], iri: Union[NamespaceIRI, str]) -> None:
        """
        Set a context. The prefix may be a QName or a valid string, the iri must be a NamespaceIRI (with a
        terminating "#" or "/").

        :param prefix: A valid prefix (QName or string)
        :param iri: A valid iri (NamespaceIRI or string)
        :return: None
        """
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        if not isinstance(iri, NamespaceIRI):
            iri = NamespaceIRI(iri)
        self._context[prefix] = iri
        self._inverse[iri] = prefix

    def __delitem__(self, prefix: Union[NCName, str]) -> None:
        """
        Delete an item. The prefix must be a QName or a valid string

        :param prefix: A valid prefix (QName or string)
        :return: None
        """
        iri: NamespaceIRI
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        try:
            iri = self._context[prefix]
        except KeyError:
            raise OmasError(f'Unknown prefix "{prefix}"')
        self._context.pop(prefix)
        self._inverse.pop(iri)

    def __iter__(self):
        """
        Returns an iterator
        """
        return self._context.__iter__()

    @property
    def graphs(self):
        return self._use

    def use(self, *args: Union[NCName, str]) -> None:
        for arg in args:
            self._use.append(NCName(arg))

    def items(self):
        """
        Returns an items() object
        """
        return self._context.items()

    def iri2qname(self, iri: Union[str, AnyIRI]) -> Union[QName, None]:
        """
        Returns a QName

        :param iri: A valid iri (NamespaceIRI or string)
        :return: QName or None
        """
        if not isinstance(iri, AnyIRI):
            iri = AnyIRI(iri)
        for prefix, trunk in self._context.items():
            if str(iri).startswith(str(trunk)):
                fragment = str(iri)[len(trunk):]
                return QName.build(str(prefix), fragment)
        return None

    def qname2iri(self, qname: Union[QName, str]) -> str:
        """
        Convert a QName into a IRI string.

        :param qname: Valid QName (Qname or str)
        :return: Full IRI as str
        """
        if not isinstance(qname, QName):
            qname = QName(qname)
        return self._context[qname.prefix] + qname.fragment


    @property
    def sparql_context(self) -> str:
        """
        Get the context ready for a SPARQL query

        :return: Context in SPARQL syntax as string
        """
        contextlist = [f"PREFIX {str(x)}: <{str(y)}>" for x, y in self._context.items()]
        return "\n".join(contextlist) + "\n"

    @property
    def turtle_context(self) -> str:
        """
        Get the context in turtle synatx

        :return: Context as turtle string
        """
        contextlist = [f"@PREFIX {str(x)}: <{str(y)}> ." for x, y in self._context.items()]
        return "\n".join(contextlist) + "\n"

    @classmethod
    def in_use(cls, name) -> bool:
        """
        Method to test if context name is already in use

        :param name: Name of the context
        :return: True or False
        """
        if cls._cache.get(name) is None:
            return False
        else:
            return True


if __name__ == '__main__':
    c1 = Context(name=DEFAULT_CONTEXT)
    c1['gaga'] = 'http://gaga.org/gugus#'
    c2 = Context(name=DEFAULT_CONTEXT)
    for k, v in c2.items():
        print(k, v)
