from dataclasses import dataclass
from enum import Enum, unique
from typing import Union, Optional, List, Set, Any, Tuple, Dict
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.langstring import Language, LangString
from omaslib.src.helpers.context import Context
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass, Attributes
from omaslib.src.propertyrestrictions import PropertyRestrictionType, PropertyRestrictions

@unique
class ResourceClassAttributes(Enum):
    SUBCLASS_OF = 'rdfs:subClassOf'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    CLOSED = 'sh:closed'

#
# Datatype definitions
#
AttributeTypes = Union[QName, LangString, bool, None]
ResourceClassAttributesContainer = Dict[ResourceClassAttributes, AttributeTypes]
Properties = Dict[BNode, Attributes]


@dataclass
class ResourceClassAttributeChange:
    old_value: Union[AttributeTypes, PropertyClass]
    action: Action
    test_in_use: bool


@strict
class ResourceClass(Model):
    _owl_class_iri: Union[QName, None]
    _attributes: ResourceClassAttributesContainer
    _properties: Dict[QName, PropertyClass]
    _changeset: Dict[Union[ResourceClassAttributes, QName], ResourceClassAttributeChange]

    def __init__(self, *,
                 con: Connection,
                 owl_class_iri: Optional[QName] = None,
                 attrs: Optional[ResourceClassAttributesContainer] = None,
                 properties: Optional[List[Union[PropertyClass, QName]]] = None):
        super().__init__(con)
        self._attributes = {}
        if attrs is not None:
            for attr, value in attrs.items():
                if (attr == ResourceClassAttributes.LABEL or attr == ResourceClassAttributes.COMMENT) and type(value) != LangString:
                    raise OmasError(f'Attribute "{attr.value}" must be a "LangString", but is "{type(value)}"!')
                if attr == ResourceClassAttributes.SUBCLASS_OF and type(value) != QName:
                    raise OmasError(f'Attribute "{attr.value}" must be a "QName", but is "{type(value)}"!')
                if attr == ResourceClassAttributes.CLOSED and type(value) != bool:
                    raise OmasError(f'Attribute "{attr.value}" must be a "bool", but is "{type(value)}"!')
                if getattr(value, 'set_notifier', None) is not None:
                    value.set_notifier(self.notifier, attr)
                self._attributes[attr] = value
        self._properties = {}
        if properties is not None:
            for prop in properties:
                newprop: PropertyClass
                if isinstance(prop, QName):
                    newprop = PropertyClass.read(self._con, prop)
                else:
                    newprop = prop
                self._properties[newprop.property_class_iri] = newprop
                newprop.set_notifier(self.notifier, newprop.property_class_iri)
        self._changeset = {}

    def __getitem__(self, key: Union[ResourceClassAttributes, QName]) -> Union[AttributeTypes, PropertyClass]:
        if type(key) is ResourceClassAttributes:
            return self._attributes[key]
        elif type(key) is QName:
            return self._properties[key]
        else:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')

    def get(self, key: Union[ResourceClassAttributes, QName]) -> Union[AttributeTypes, PropertyClass, None]:
        if type(key) is ResourceClassAttributes:
            return self._attributes.get(key)
        elif type(key) is QName:
            return self._attributes.get(key)
        else:
            return None

    def __setitem__(self, key: Union[ResourceClassAttributes, QName], value: Union[AttributeTypes, PropertyClass]) -> None:
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)
        if type(key) is ResourceClassAttributes:
            if self._attributes.get(key) is None:  # Attribute not yet set
                if self._changeset.get(key) is None:  # Only first change is recorded
                    self._changeset[key] = ResourceClassAttributeChange(None, Action.CREATE, False)  # TODO: Check if "check_in_use" must be set
            else:
                if self._changeset.get(key) is None:  # Only first change is recorded
                    self._changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.REPLACE, False)  # TODO: Check if "check_in_use" must be set
            self._attributes[key] = value
        elif type(key) is QName:
            if self._properties.get(key) is None:  # Property not yet set
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassAttributeChange(self._properties[key], Action.CREATE, False)
            else:
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassAttributeChange(self._properties[key], Action.REPLACE, False)
            self._properties = value
        else:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')

    def __delitem__(self, key: Union[ResourceClassAttributes, QName]) -> None:
        if type(key) is ResourceClassAttributes:
            if self._changeset.get(key) is None:
                self._changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.DELETE, False)
            del self._attributes[key]
        elif type(key) is QName:
            if self._changeset.get(key) is None:
                self._changeset[key] = ResourceClassAttributeChange(self._properties[key], Action.DELETE, False)
            del self._properties[key]
        else:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')


    def properties_items(self):
        return self._properties.items()

    def attributes_items(self):
        return self._attributes.items()

    def __str__(self):
        blank = ' '
        indent = 2
        s = f'Shape: {self._owl_class_iri}Shape\n'
        s += f'{blank:{indent*1}}Attributes:\n'
        for attr, value in self._attributes.items():
            s += f'{blank:{indent*2}}{attr.value} = {value}\n'
        s += f'{blank:{indent*1}}Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for qname, prop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {prop}\n'
        return s

    def notifier(self, what: Union[ResourceClassAttributes, QName]):
        self._changeset[what] = ResourceClassAttributeChange(None, Action.MODIFY, True)

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?resinstances) as ?nresinstances)
        WHERE {{
            ?resinstance rdf:type {self._owl_class_iri} .
            FILTER(?resinstances != {self._owl_class_iri}Shape)
        }} LIMIT 2
        """
        res = self._con.rdflib_query(query)
        if len(res) != 1:
            raise OmasError('Internal Error in "ResourceClass.in_use"')
        for r in res:
            if int(r.nresinstances) > 0:
                return True
            else:
                return False

    def to_sparql_insert(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}{self._shape} a sh:NodeShape, {self._owl_class_iri} ;\n'
        sparql += f'{blank:{indent + 4}}sh:targetClass {self._owl_class_iri} ; \n'
        for p in self._properties:
            sparql += f'{blank:{(indent + 1) * indent_inc}}sh:property\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}[\n'
            sparql += f'{blank:{(indent + 3) * indent_inc}}sh:path rdf:type ;\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}] ;\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}sh:property\n'

            sparql += p.create_shacl(indent + 8)
        sparql += f'{blank:{indent}}sh:closed {"true" if self._closed else "false"} .\n'
        return sparql

    @staticmethod
    def __query_shacl(con: Connection, owl_class_iri: QName) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value ?propiri ?propshape
        FROM {owl_class_iri.prefix}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value
        }}
         """
        res = con.rdflib_query(query)
        attributes: Attributes = {}
        for r in res:
            attriri = context.iri2qname(r['attriri'])
            if attriri == QName('rdf:type'):
                tmp_owl_class_iri = context.iri2qname(r[1])
                if tmp_owl_class_iri == QName('sh:NodeShape'):
                    continue
                if tmp_owl_class_iri != owl_class_iri:
                    raise OmasError(f'Inconsistent Shape for "{owl_class_iri}": rdf:type="{tmp_owl_class_iri}"')
            elif attriri == QName('sh:property'):
                continue  # processes later – points to a BNode containing
            else:
                attriri = context.iri2qname(r['attriri'])
                if isinstance(r['value'], URIRef):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(context.iri2qname(r['value']))
                elif isinstance(r['value'], Literal):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    if r['value'].language is None:
                        attributes[attriri].append(r['value'].toPython())
                    else:
                        attributes[attriri].append(r['value'].toPython() + '@' + r['value'].language)
                elif isinstance(r['value'], BNode):
                    pass
                else:
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
        return attributes

    def parse_shacl(self, attributes: Attributes) -> None:
        for key, val in attributes.items():
            if key == 'dcterms:hasVersion':
                self.__version = SemanticVersion.fromString(val[0])
            elif key == 'dcterms:creator':
                self.__creator = val[0]
            elif key == 'dcterms:created':
                self.__created = val[0]
            elif key == 'dcterms:contributor':
                self.__contributor = val[0]
            elif key == 'dcterms:modified':
                self.__modified = val[0]
            elif key in ResourceClassAttributes:
                attr = ResourceClassAttributes(key)
                self._attributes[attr] = val[0]
            else:
                raise OmasError(f'Invalid shacl definition of ResourceClass attribute: "{key} {val}"')


    @staticmethod
    def __query_resource_props(con: Connection, owl_class_iri: QName) -> List[Union[PropertyClass, QName]]:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {owl_class_iri.prefix}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape sh:property ?prop .
            OPTIONAL {{
                ?prop ?attriri ?value .
                OPTIONAL {{
                    ?value rdf:rest*/rdf:first ?oo
                }}
            }}
        }}
        """
        res = con.rdflib_query(query)
        properties: Dict[QName, PropertyClass] = {}
        for r in res:
            if r['value'] == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                continue
            if not isinstance(r['attriri'], URIRef):
                raise OmasError("INCONSISTENCY!")
            propnode = r['prop']  # this is usually a BNode
            prop: Union[PropertyClass, QName]
            if isinstance(propnode, URIRef):
                prop = context.iri2qname(propnode)
            elif isinstance(propnode, BNode):
                if properties.get(propnode) is None:
                    properties[propnode]: Attributes = {}
                attributes: Attributes = properties[propnode]
                PropertyClass.process_triple(context, r, attributes)
                if not properties.get(property):
                    properties[property] = Attributes({})  # of type Attributes
                attributes: Attributes = properties[property]
                prop = PropertyClass(con=con)
                prop.parse_shacl(attributes=attributes)
            else:
                raise OmasError(f'Unexpected type for propnode in SHACL. Type = "{type(propnode)}".')
            properties.append(prop)
        return properties

    def __read_shacl(self) -> None:
        """
        Read the shacl definition from the triple store and create the respective ResourceClass
        and PropertyClass instances which represent the Shape and OWL definitions in Python.

        :return: None
        """
        context = Context(name=self._con.context_name)
        if not self._owl_class_iri:
            raise OmasError('ResourceClass must be created with "owl_class" given as parameter!')

        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o ?propiri ?propshape
        FROM {self._owl_class_iri.prefix}:shacl
        WHERE {{
            BIND({str(self._owl_class_iri)}Shape AS ?shape)
            ?shape ?p ?o
            OPTIONAL {{
                {{ ?o sh:path ?propiri . }} UNION {{ ?o sh:propertyShape ?propshape }}
            }}
        }}
         """
        res = con.rdflib_query(query1)
        self._subclass_of = None
        self._label = None
        self._comment = None
        self._closed = True
        propiris: List[QName] = []
        propshapes: List[QName] = []
        for r in res:
            p = context.iri2qname(r[0])
            if p == 'rdf:type':
                tmp_qname = context.iri2qname(r[1])
                if tmp_qname == QName('sh:NodeShape'):
                    continue
                if self._owl_class_iri is None:
                    self._owl_class_iri = tmp_qname
                else:
                    if tmp_qname != self._owl_class_iri:
                        raise OmasError(f'Inconsistent Shape for "{self._owl_class_iri}": rdf:type="{tmp_qname}"')
            elif p == 'rdfs:label':
                ll = Language(r[1].language) if r[1].language else Language.XX
                if self._label is None:
                    self._label = LangString({ll: r[1].toPython()})
                else:
                    self._label[ll] = r[1].toPython()
            elif p == 'rdfs:comment':
                ll = Language(r[1].language) if r[1].language else Language.XX
                if self._comment is None:
                    self._comment = LangString({ll: r[1].toPython()})
                else:
                    self._comment[ll] = r[1].toPython()
            elif p == 'rdfs:subClassOf':
                tmpstr = context.iri2qname(r[1])
                i = str(tmpstr).find('Shape')
                if i == -1:
                    raise OmasError('Shape not valid......')  # TODO: Correct error message
                self._subclass_of = QName(str(tmpstr)[:i])
            elif p == 'sh:targetClass':
                tmp_qname = context.iri2qname(r[1])
                if self._owl_class_iri is None:
                    self._owl_class_iri = tmp_qname
                else:
                    if tmp_qname != self._owl_class_iri:
                        raise OmasError(f'Inconsistent Shape for "{self._owl_class_iri}": sh:targetClass="{tmp_qname}"')
            elif p == 'sh:closed':
                self._closed = closed = r[1].value
            elif p == 'sh:property':
                if r[2] is not None:
                    propiris.append(context.iri2qname(r[2]))
                if r[3] is not None:
                    propshapes.append(context.iri2qname(r[3]))

        # TODO: read all propiris and propshapes. Move and adapt the code below to PropertClass.py !!!

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {self._owl_class_iri.prefix}:shacl
        WHERE {{
            BIND({str(self._owl_class_iri)}Shape AS ?shape)
            ?shape sh:property ?prop .
            ?prop ?attriri ?value .
            OPTIONAL {{
                ?value rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = con.rdflib_query(query2)
        properties: Properties = Properties({})
        for r in res:
            if r['value'] == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                continue
            if not isinstance(r['attriri'], URIRef):
                raise OmasError("INCONSISTENCY!")
            property = r['prop']  # this is usually a BNode
            if not properties.get(property):
                properties[property] = Attributes({})  # of type Attributes
            attributes: Attributes = properties[property]
            PropertyClass.process_triple(context, r, attributes)
            prop = PropertyClass(con=con)
            prop.parse_shacl(attributes=attributes)
            self._properties[prop.property_class_iri] = prop

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owl_class_iri.prefix}:onto
        WHERE {{
   	        omas:OmasProject rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
        }}
        """
        res = self._con.rdflib_query(query1)
        propdict = {}
        for r in res:
            bnode_id = str(r[0])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
            p = context.iri2qname(str(r[1]))
            pstr = str(p)
            if pstr == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
            elif pstr == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = context.iri2qname(str(r[2]))
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{pstr}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OmasError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x == property_iri]
            if len(prop) != 1:
                OmasError(f'Property "{property_iri}" from OWL has no SHACL definition!')
            self._properties[prop[0]].prop.read_owl()

    @classmethod
    def read(cls, con: Connection, owl_class_iri: QName) -> 'ResourceClass':
        attributes = ResourceClass.__query_shacl(con, owl_class_iri=owl_class_iri)
        properties = ResourceClass.__query_resource_props(con=con, owl_class_iri=owl_class_iri)
        resclass = cls(con=con, owl_class_iri=owl_class_iri, properties=properties)
        resclass.parse_shacl(attributes=attributes)
        resclass.__read_owl()
        return resclass

    def __create_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'

        for iri, p in self._properties.items():
            if p.exclusive_for_class is None:
                sparql += "\n"
                sparql += f'{blank:{(indent + 2)*indent_inc}}{iri}Shape a sh:PropertyShape ;\n'
                sparql += p.property_node_shacl(4) + " .\n"
                sparql += "\n"

        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class_iri}Shape a sh:NodeShape, {self._owl_class_iri} ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of}Shape ;\n'
        sparql += f'{blank:{(indent + 3)*indent_inc}}sh:targetClass {self._owl_class_iri} ;\n'
        if self._label:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:label {self._label} ;\n'
        if self._comment:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:comment {self._comment} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}sh:property\n'
        sparql += f'{blank:{(indent + 4) * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 5) * indent_inc}}sh:path rdf:type ;\n'
        sparql += f'{blank:{(indent + 4) * indent_inc}}] ;\n'
        for iri, p in self._properties.items():
            if p.exclusive_for_class:
                sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property [\n'
                sparql += p.property_node_shacl(4) + ' ;\n'
                sparql += f'{blank:{(indent + 3) * indent_inc}}] ;\n'
            else:
                sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property {iri}Shape ;\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}sh:closed {"true" if self._closed else "false"} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            #print(sparql)
            self._con.update_query(sparql)

    def __create_owl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False):
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:onto {{\n'
        for iri, p in self._properties.items():
            sparql += p.create_owl_part1(indent + 2) + '\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class_iri} rdf:type owl:Class ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of} ,\n'
        else:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf\n'
        i = 0
        for iri, p in self._properties.items():
            sparql += p.create_owl_part2(indent + 4)
            if i < len(self._properties) - 1:
                sparql += ' ,\n'
            else:
                sparql += ' .\n'
            i += 1
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            #print(sparql)
            self._con.update_query(sparql)

    def create(self, as_string: bool = False) -> Union[str, None]:
        if as_string:
            rdfdata = self.__create_shacl(as_string=as_string)
            rdfdata += self.__create_owl(as_string=as_string)
            return rdfdata
        else:
            self.__create_shacl(as_string)
            self.__create_owl(as_string)

    def __update_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        if not self._changeset:
            if as_string:
                return ''
            else:
                return
        sparql_switch1 = {
            ResourceClassAttributes.SUBCLASS_OF: '?shape rdfs:subClassOf ?subclass_of .',
            ResourceClassAttributes.CLOSED: '?shape sh:closed ?closed .',
            ResourceClassAttributes.LABEL: '?shape rdfs:label ?label .',
            ResourceClassAttributes.COMMENT: '?shape rdfs:comment ?comment .',
            ResourceClassAttributes.PROPERTY: '?shape sh:property ?propnode'
        }
        sparql_switch2 = {
            ResourceClassAttributes.SUBCLASS_OF: f'?shape rdfs:subClassOf {self._subclass_of}Shape .',
            ResourceClassAttributes.CLOSED: f'?shape sh:closed {"true" if self._closed else "false"} .',
            ResourceClassAttributes.LABEL: f'?shape rdfs:label {self._label} .',
            ResourceClassAttributes.COMMENT: f'?shape rdfs:comment {self._comment} .',
            ResourceClassAttributes.PROPERTY: ''
        }
        sparql_switch3 = {
            ResourceClassAttributes.SUBCLASS_OF: 'OPTIONAL { ?shape rdfs:subClassOf ?subclass_of }',
            ResourceClassAttributes.CLOSED: 'OPTIONAL { ?shape sh:closed ?closed }',
            ResourceClassAttributes.LABEL: 'OPTIONAL { ?shape rdfs:label ?label }',
            ResourceClassAttributes.COMMENT: 'OPTIONAL { ?shape rdfs:comment ?comment }',
            ResourceClassAttributes.PROPERTY: 'OPTIONAL { ?shape sh:property ?propnode }'
        }

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        n = len(self._changeset)
        i = 1
        do_it = False
        for name, action, prop_iri in self._changeset:
            if name == ResourceClassAttributes.PROPERTY:
                print(self._properties)
                sparql_switch2[ResourceClassAttributes.PROPERTY] = '?shape sh:property [\n' + self._properties[prop_iri].property_node_shacl(indent + 1) + ' ; ]'
                if action == Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch1[name]}\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                    sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
                    sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
                    sparql += f'{blank:{(indent + 2)*indent_inc}}?shape rdf:type sh:NodeShape .\n'
                    sparql += f'{blank:{(indent + 2)*indent_inc}}?shape sh:targetClass {self._owl_class_iri} .\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch3[name]}\n'
                    sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                    sparql += f'{blank:{indent*indent_inc}}}}{"" if i == n else " ;"}\n'

            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch1[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch2[name]}\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape rdf:type sh:NodeShape .\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape sh:targetClass {self._owl_class_iri} .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch3[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}{"" if i == n else " ;"}\n'
            i += 1
            do_it = True
        if as_string:
            return sparql
        else:
            if do_it:
                self._con.update_query(sparql)

    def __update_owl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        action = None
        if (ResourceClassAttributes.SUBCLASS_OF, Action.DELETE) in self._changeset:
            action = Action.DELETE
        elif (ResourceClassAttributes.SUBCLASS_OF, Action.REPLACE) in self._changeset:
            action = Action.REPLACE
        elif (ResourceClassAttributes.SUBCLASS_OF, Action.CREATE) in self._changeset:
            action = Action.CREATE

        if action:
            blank = ''
            context = Context(name=self._con.context_name)
            sparql = context.sparql_context
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:onto {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class_iri} rdfs:subClassOf ?subclass_of .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class_iri} rdfs:subClassOf {self._subclass_of} .'
                sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class_iri} rdf:type owl:Class .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}OPTIONAL {{\n'
            sparql += f'{blank:{(indent + 3)*indent_inc}}{self._owl_class_iri} rdfs:subClassOf ?subclass_of .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}}}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'
            if as_string:
                return sparql
            else:
                self._con.update_query(sparql)
        else:
            if as_string:
                return ''
            else:
                return

    def update(self, as_string: bool = False) -> Union[str, None]:
        if as_string:
            tmp = self.__update_shacl(as_string=True)
            #print(tmp)
            tmp += self.__update_owl(as_string=True)
            return tmp
        else:
            self.__update_shacl()
            self.__update_owl()


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass(con, QName('omas:Project'))
    omas_project.read()
    #print(omas_project)
    #print(omas_project.create(as_string=True))
    #exit(0)
    #omas_project.label = LangString({Languages.EN: '*Omas Project*', Languages.DE: '*Omas-Projekt*'})
    #omas_project.comment_add(Languages.FR, 'Un project pour OMAS')
    #omas_project.closed = False
    #omas_project.subclass_of = QName('omas:Object')
    omas_project[QName('omas:projectEnd')].name = LangString({Language.DE: "Projektende"})
    print(omas_project.update(as_string=True))
    # omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    # omas_project2.read()
    # print(omas_project2)
    # exit(0)
    #omas_project.closed = False
    #omas_project.update()
    #omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    #omas_project2.read()
    #print(omas_project2)
    #exit(0)
    #print(omas_project)
    #omas_project.create()
    #exit(-1)
    pdict = {
        QName('omas:commentstr'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:commentstr'),
                      datatype=XsdDatatypes.string,
                      exclusive_for_class=QName('omas:OmasComment'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          language_in={Language.DE, Language.EN},
                          unique_lang=True
                      ),
                      name=LangString({Language.EN: "Comment"}),
                      description=LangString({Language.EN: "A comment to anything"}),
                      order=1),
        QName('omas:creator'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=2),
        QName('omas:createdAt'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=3)
    }
    comment_class = ResourceClass(
        con=con,
        owl_class_iri=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        label=LangString({Language.EN: 'Omas Comment', Language.DE: 'Omas Kommentar'}),
        comment=LangString({Language.EN: 'A class to comment something...'}),
        properties=pdict,
        closed=True
    )
    comment_class.create()
    comment_class = None
    comment_class2 = ResourceClass(con=con, owl_class_iri=QName('omas:OmasComment'))
    comment_class2.read()
    print(comment_class2)
