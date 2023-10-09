import json
import datetime
import urllib
import requests
from enum import Enum, unique

from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union, Mapping
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from rdflib.query import Result
from rdflib.term import Identifier
from requests import get, post
from pathlib import Path
from urllib.parse import quote_plus

from omaslib.src.helpers.datatypes import QName
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT


@unique
class SparqlResultFormat(Enum):
    """
    Enumeration of formats that may be returned by the triple store (if the specific store supports these)
    """
    XML ="application/sparql-results+xml"
    JSON = "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8" # Accept: application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8
    TURTLE = "text/turtle"
    N3 = "text/rdf+n3"
    NQUADS = "text/x-nquads"
    JSONLD = "application/ld+json"
    TRIX = "application/trix"
    TRIG = "application/x-trig"
    TEXT = "text/plain"


@strict
class Connection:
    """
    Class that implements the connection to an external triple store for omaslib.

    The connection to a SPARQL endpoint requires the following information:

    * _server_: URL of the server (inlcuding port number)
    * _repo_: Name of the repository to connect to
    * _context_name_: Name of the context (see ~helper.Context)

    The class implements the following methods:

    * Getter-methods:
        - _server_: returns the server string
        - _repo_: returns the repository name
        - _context_name_: returns the context name
    * Setter methods:
        - Any setting of the _server_, _repo_ or _context_name_ - variables raises an OmasError-exception
    * Further methods
        - _Constructor(server,repo,contextname)_: requires _server_ and _repo_string, _context_name defaults to "DEFAULT"
        - _clear_graph_(graph_name: QName)_: Deletes the given graph (must be given as QName)
        - _clear_repo()_ Deletes all data in the repository given by the Connection instance
        - _upload_turtle(filename: str, graphname:str)_: Loads the data in the given file (must be turtle or trig
          format) into the given repo and graph. If graphname is not given, the data will either be loaded into the
          default graph of the repository or into the graph given in the trig file.
          _Note_: The method returns before the triple store has digested all the data! It may not immediately
          available after this method returns!
        - _query(query: str, format: SparqlResultFormat)_: Sends a SPARQL query to the triple store and returns the
          result in the given format. If no format is given, JSON will be used as default format.
        - _update_query(query: str)_: Send a SPARQL update query to the SPARQL endpoint. The method return either
          {'status': 'OK'} or {'status': 'ERROR', 'message': 'error-text'}
        - _rdflib_query(query: str, bindings: Optional[Mapping[str, Identifier]])_: Send a SPAQRL query using rdflib
          to the SPARQL endpoint. The variable _bindings_ allows to set query parameters to given values.

    """
    _server: str
    _repo: str
    _context_name: str
    _store: SPARQLUpdateStore
    _query_url: str
    _update_url: str
    _switcher = {
        SparqlResultFormat.XML: lambda a: a.text,
        SparqlResultFormat.JSON: lambda a: a.json(),
        SparqlResultFormat.TURTLE: lambda a: a.text,
        SparqlResultFormat.N3: lambda a: a.text,
        SparqlResultFormat.NQUADS: lambda a: a.text,
        SparqlResultFormat.JSONLD: lambda a: a.json(),
        SparqlResultFormat.TRIX: lambda a: a.text,
        SparqlResultFormat.TRIG: lambda a: a.text,
        SparqlResultFormat.TEXT: lambda a: a.text
    }

    def __init__(self, server: str, repo: str, context_name: str = DEFAULT_CONTEXT) -> None:
        """
        Constructor that establishes the connection parameters.

        :param server: URL of the server (including port information if necessary)
        :param repo: Name of the repository on the server
        :param context_name: A name of the Context to be used (see ~Context). If no such context exists,
            a new context of this name is created
        """
        self._server = server
        self._repo = repo
        self._context_name = context_name
        self._query_url = f'{self._server}/repositories/{self._repo}'
        self._update_url = f'{self._server}/repositories/{self._repo}/statements'
        self._store = SPARQLUpdateStore(self._query_url, self._update_url)
        context = Context(name=context_name)
        for prefix, iri in context.items():
            self._store.bind(str(prefix), Namespace(str(iri)))

    @property
    def server(self) -> str:
        """Getter for server string"""
        return self._server

    @server.setter
    def server(self, value: Any) -> None:
        """Catch setting the server and raise a ~helpers.OmasError"""
        raise OmasError('Cannot change the server of a connection!')

    @property
    def repo(self) -> str:
        """Getter for repository name"""
        return self._repo

    @repo.setter
    def repo(self, value: Any) -> None:
        """Catch setting the repository name and raise a ~helpers.OmasError"""
        raise OmasError('Cannot change the repo of a connection!')

    @property
    def context_name(self) -> str:
        """Getter for the context name"""
        return self._context_name

    @context_name.setter
    def context_name(self, value: Any) -> None:
        """Catch setting the context name and raise a ~helpers.OmasError"""
        raise OmasError('Cannot change the context name of a connection!')

    def clear_graph(self, graph_iri: QName) -> None:
        """
        This method clears (deletes) the given RDF graph. May raise an ~herlper.OmasError.

        :param graph_iri: RDF graph name as QName. The prefix must be defined in the context!
        :return: None
        """
        context = Context(name=self._context_name)
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/json, text/plain, */*",
        }
        data = f"CLEAR GRAPH <{context.qname2iri(graph_iri)}>"
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data)
        if not req.ok:
            raise OmasError(req.text)

    def clear_repo(self) -> None:
        """
        This method deletes the complete repository. Use with caution!!!

        :return: None
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
        }
        data = {"update": "CLEAR ALL"}
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data)
        if not req.ok:
            raise OmasError(req.text)

    def upload_turtle(self, filename: str, graphname: Optional[str] = None) -> None:
        """
        Upload a turtle- or trig-file to the given repository. This method returns immediately after sending the
        command to upload the given file to the triplestore. The import process may take a while!

        :param filename: Name of the file to upload
        :param graphname: Optional name of the RDF-graph where the data should be imported in.
        :return: None
        """
        with open(filename, encoding="utf-8") as f:
            content = f.read()
            ext = Path(filename).suffix
            mime = ""
            if ext == ".ttl":
                mime = "text/turtle"
            elif ext == ".trig":
                mime = "application/x-trig"

            ct = datetime.datetime.now()
            ts = ct.timestamp()
            data = {
                "name": f'Data from "{filename}"',
                "status": None,
                "message": "",
                "context": graphname,
                "replaceGraphs": [],
                "baseURI": None,
                "forceSerial": False,
                "type": "text",
                "format": mime,
                "data": content,
                "timestamp": ts,
                "parserSettings": {
                    "preserveBNodeIds": False,
                    "failOnUnknownDataTypes": False,
                    "verifyDataTypeValues": False,
                    "normalizeDataTypeValues": False,
                    "failOnUnknownLanguageTags": False,
                    "verifyLanguageTags": True,
                    "normalizeLanguageTags": True,
                    "stopOnError": True
                }
            }
            jsondata = json.dumps(data)
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json; charset=utf-8"
            }
            url = f"{self._server}/rest/repositories/{self._repo}/import/upload/text"
            req = requests.post(url,
                                headers=headers,
                                data=jsondata)
        if not req.ok:
            raise OmasError(req.text)

    def query(self, query: str, format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        """
        Send a SPARQL-query and return the result. The result may be nested dict (in case of JSON) or a text.

        :param query: SPARQL query as string
        :param format: The format desired (see ~SparqlResultFormat)
        :return: Query results or an error message (as text)
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": format.value,
        }
        data = {
            'query': query,
        }
        res = requests.post(url=self._query_url,
                            headers=headers,
                            data=data)
        if res.status_code == 200:
            return Connection._switcher[format](res)
        else:
            return res.text

    def update_query(self, query: str) -> Dict[str,str]:
        """
        Send an SPARQL UPDATE query to the triple store
        :param query: SPARQL UPDATE query as string
        :return:
        """
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/statements"
        res = requests.post(url, data={"update": query}, headers=headers)
        if res.status_code == 204:
            return {'status': 'OK'}
        else:
            return {'status': 'ERROR', 'message': res.text}

    def rdflib_query(self, query: str,
                     bindings: Optional[Mapping[str, Identifier]] = None) -> Result:
        """
        Send a SPARQL query to a triple store using the Python rdflib interface.

        :param query: SPARQL query string
        :param bindings: Bindings to variables
        :return: a RDFLib Result instance
        """
        return self._store.query(query, initBindings=bindings)


if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     context_name="DEFAULT")
    con.clear_repo()
    con.upload_turtle("../ontologies/omas.ttl", "http://omas.org/base#onto")
    con.upload_turtle("../ontologies/omas.shacl.trig")
