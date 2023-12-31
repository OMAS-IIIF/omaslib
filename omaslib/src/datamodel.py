from datetime import datetime
from typing import Dict, List, Optional, Union

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.resourceclass import ResourceClass


class DataModel(Model):
    __graph: NCName
    __context: Context
    __creator: Optional[QName]
    __created: Optional[datetime]
    __contributor: Optional[QName]
    __modified: Optional[datetime]
    __propclasses: Dict[QName, PropertyClass]
    __resclasses: Dict[QName, ResourceClass]

    def __init__(self, *,
                 con: Connection,
                 graph: NCName,
                 propclasses: Optional[List[PropertyClass]] = None,
                 resclasses: Optional[List[ResourceClass]] = None) -> None:
        super().__init__(con)
        self.__graph = graph
        self.__propclasses = {}
        if propclasses is not None:
            for p in propclasses:
                self.__propclasses[p.property_class_iri] = p
        self.__resclasses = {}
        if resclasses is not None:
            for r in resclasses:
                self.__resclasses[r.owl_class_iri] = r

    def get_propclasses(self) -> List[QName]:
        return [x for x in self.__propclasses]

    def get_propclass(self, propclass_iri: QName) -> Union[PropertyClass, None]:
        return self.__propclasses.get(propclass_iri)

    def get_resclasses(self) -> List[QName]:
        return [x for x in self.__resclasses]

    def get_resclass(self, resclass_iri: QName) ->  Union[ResourceClass, None]:
        return self.__resclasses.get(resclass_iri)

    def create(self):
        pass


    @classmethod
    def read(cls, con: Connection, graph: NCName):
        cls.__graph = graph
        cls.__context = Context(name=cls.__graph)
        #
        # first we read the shapes metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?creator ?created ?contributor ?modified
        FROM {cls.__graph}:shacl
        WHERE {{
           {cls.__graph}:shapes dcterms:creator ?creator .
           {cls.__graph}:shapes dcterms:created ?created .
           {cls.__graph}:shapes dcterms:contributor ?contributor .
           {cls.__graph}:shapes dcterms:modified ?modified .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        cls.__created = res[0]['created']
        cls.__creator = res[0]['creator']
        cls.__modified = res[0]['modified']
        cls.__contributor = res[0]['contributor']
        #
        # now we read the OWL ontology metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?creator ?created
        FROM {cls.__graph}:onto
        WHERE {{
           {cls.__graph}:ontology dcterms:creator ?creator .
           {cls.__graph}:ontology dcterms:created ?created .
           {cls.__graph}:ontology dcterms:contributor ?contributor .
           {cls.__graph}:ontology dcterms:modified ?modified .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        #
        # now get the QNames of all standalone properties within the data model
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?prop
        FROM {cls.__graph}:shacl
        WHERE {{
            ?prop a sh:PropertyShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        propclasses = []
        for r in res:
            propnameshacl = str(r['prop'])
            propclassiri = propnameshacl.removesuffix("Shape")
            propclass = PropertyClass.read(con, graph, QName(propclassiri))
            propclasses.append(propclass)
        #
        # now get all resources defined in the data model
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?shape
        FROM {cls.__graph}:shacl
        WHERE {{
            ?shape a sh:NodeShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        resclasses = []
        for r in res:
            resnameshacl = str(r['shape'])
            resclassiri = resnameshacl.removesuffix("Shape")
            resclass = ResourceClass.read(con, graph, QName(resclassiri))
            resclasses.append(resclass)
        return cls(graph=graph, con=con, propclasses=propclasses, resclasses=resclasses)



