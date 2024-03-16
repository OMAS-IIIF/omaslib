import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, NCName, Xsd_anyURI
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorValue, OmasErrorNoPermission, OmasError
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.user import User
from omaslib.src.in_project import InProjectClass


class TestUser(unittest.TestCase):
    _context: Context
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUp(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="omas",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")

        # user = User(con=cls._connection, userId=NCName("coyote"))
        # user.delete()
        cls._connection.clear_graph(QName('omas:admin'))
        cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    def test_constructor(self):
        user = User(con=self._connection,
                    userId=NCName("testuser"),
                    familyName="Test",
                    givenName="Test",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})

        self.assertEqual(user.userId, NCName("testuser"))
        self.assertEqual(user.familyName, "Test")
        self.assertEqual(user.givenName, "Test")
        self.assertEqual(user.inProject, InProjectClass({QName("omas:HyperHamlet"): {
            AdminPermission.ADMIN_USERS,
            AdminPermission.ADMIN_RESOURCES,
            AdminPermission.ADMIN_CREATE
        }}))
        self.assertEqual(user.hasPermissions, {QName('omas:GenericView')})

    # @unittest.skip('Work in progress')
    def test_read_user(self):
        user = User.read(con=self._connection, userId="rosenth")
        self.assertEqual(user.userId, NCName("rosenth"))
        self.assertEqual(user.userIri, Xsd_anyURI("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.familyName, "Rosenthaler")
        self.assertEqual(user.givenName, "Lukas")
        self.assertEqual(user.inProject, InProjectClass({
            QName("omas:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            QName('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.hasPermissions, {QName("omas:GenericRestricted"), QName('omas:GenericView')})

    # @unittest.skip('Work in progress')
    def test_read_unknown_user(self):
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="nosuchuser")
        self.assertEqual(str(ex.exception), 'User "nosuchuser" not found.')

    # @unittest.skip('Work in progress')
    def test_search_user(self):
        users = User.search(con=self._connection, userId="fornaro")
        self.assertEqual([Xsd_anyURI("https://orcid.org/0000-0003-1485-4923")], users)

        users = User.search(con=self._connection, familyName="Rosenthaler")
        self.assertEqual([Xsd_anyURI("https://orcid.org/0000-0003-1681-4036")], users)

        users = User.search(con=self._connection, givenName="John")
        self.assertEqual([Xsd_anyURI("urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b")], users)

        users = User.search(con=self._connection, inProject=QName("omas:HyperHamlet"))
        self.assertEqual([Xsd_anyURI("https://orcid.org/0000-0003-1681-4036"),
                          Xsd_anyURI("https://orcid.org/0000-0003-1485-4923"),
                          Xsd_anyURI("https://orcid.org/0000-0001-9277-3921")], users)

        users = User.search(con=self._connection, inProject=Xsd_anyURI("http://www.salsah.org/version/2.0/SwissBritNet"))
        self.assertEqual([Xsd_anyURI("urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b")], users)

        users = User.search(con=self._connection, userId="GAGA")
        self.assertEqual([], users)

    # @unittest.skip('Work in progress')
    def test_search_user_injection(self):
        with self.assertRaises(OmasErrorValue) as ex:
            users = User.search(con=self._connection, userId="fornaro\".}\nSELECT * WHERE {?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string "fornaro".}\nSELECT * WHERE {?s ?p ?s})#" for NCName')

        users = User.search(con=self._connection, familyName="Rosenthaler\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)
        users = User.search(con=self._connection, givenName="John\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)

        with self.assertRaises(OmasErrorValue) as ex:
            users = User.search(con=self._connection, inProject="omas:HyperHamlet\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string "omas:HyperHamlet".}\nSELECT * WHERE{?s ?p ?s})#" for anyIRI')

    # @unittest.skip('Work in progress')
    def test_create_user(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0003-3478-9313"),
                    userId=NCName("coyote"),
                    familyName="Coyote",
                    givenName="Wiley E.",
                    credentials="Super-Genius",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')},
                    isActive=True)
        user.create()
        user2 = User.read(con=self._connection, userId="coyote")
        self.assertEqual(user2.userId, user.userId)
        self.assertEqual(user2.userIri, user.userIri)
        self.assertEqual(user2.familyName, user.familyName)
        self.assertEqual(user2.givenName, user.givenName)
        self.assertEqual(user2.inProject, user.inProject)
        self.assertEqual(user2.hasPermissions, user.hasPermissions)
        self.assertTrue(user2.isActive)

    # @unittest.skip('Work in progress')
    def test_create_user_no_admin_perms(self):
        user = User(con=self._connection,
                    userId=NCName("birdy"),
                    familyName="Birdy",
                    givenName="Tweetie",
                    credentials="Sylvester",
                    inProject={QName('omas:HyperHamlet'): {}},
                    hasPermissions={QName('omas:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=NCName("birdy"))
        self.assertEqual(user.familyName, "Birdy")

    # @unittest.skip('Work in progress')
    def test_create_user_no_in_project(self):
        user = User(con=self._connection,
                    userId=NCName("yogi"),
                    familyName="Baer",
                    givenName="Yogi",
                    credentials="BuBu",
                    hasPermissions={QName('omas:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=NCName("yogi"))
        self.assertEqual(user.familyName, "Baer")

    # @unittest.skip('Work in progress')
    def test_create_user_no_permset(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0003-3478-9313"),
                    userId=NCName("speedy"),
                    familyName="Ganzales",
                    givenName="Speedy",
                    credentials="fasterthanlight",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=NCName("speedy"))
        self.assertEqual(user.familyName, "Ganzales")


    # @unittest.skip('Work in progress')
    def test_create_user_no_useriri(self):
        user = User(con=self._connection,
                    userId=NCName("sylvester"),
                    familyName="Sylvester",
                    givenName="Cat",
                    credentials="Birdy",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')},
                    isActive=False)
        user.create()
        del user
        user = User.read(con=self._connection, userId=NCName("sylvester"))
        self.assertTrue(str(user.userIri).startswith("urn:uuid:"))
        self.assertFalse(user.isActive)

    # @unittest.skip('Work in progress')
    def test_create_user_duplicate_userid(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0003-3478-9314"),
                    userId=NCName("fornaro"),
                    familyName="di Fornaro",
                    givenName="Petri",
                    credentials="Genius",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user ID "fornaro" already exists')

    # @unittest.skip('Work in progress')
    def test_create_user_duplicate_useriri(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0003-1681-4036"),
                    userId=NCName("brown"),
                    familyName="Brown",
                    givenName="Emmett",
                    credentials="Time-Machine@1985",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user IRI "https://orcid.org/0000-0003-1681-4036" already exists')

    # @unittest.skip('Work in progress')
    def test_create_user_invalid_project(self):
        user = User(con=self._connection,
                    userId=NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={QName('omas:NotExistingproject'): {AdminPermission.ADMIN_USERS,
                                                                  AdminPermission.ADMIN_RESOURCES,
                                                                  AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the projects is not existing!')

    # @unittest.skip('Work in progress')
    def test_create_user_invalid_permset(self):
        user = User(con=self._connection,
                    userId=NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView'), QName('omas:Gaga')})
        with self.assertRaises(OmasErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')

    # @unittest.skip('Work in progress')
    def test_create_user_no_privilege(self):
        user = User(con=self._unpriv,
                    userId=NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Xsd_anyURI('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'No permission to create user in project http://www.salsah.org/version/2.0/SwissBritNet.')

    # @unittest.skip('Work in progress')
    def test_create_user_no_connection(self):
        user = User(userId=NCName("brown"),
                    familyName="Dock",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Xsd_anyURI('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasError) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'Cannot create: no connection')

    # @unittest.skip('Work in progress')
    def test_delete_user(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0002-9991-2055"),
                    userId=NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        self.assertEqual(user2.userIri, user.userIri)
        user2.delete()
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="edison")
        self.assertEqual(str(ex.exception), 'User "edison" not found.')

    # @unittest.skip('Work in progress')
    def test_delete_user_unpriv(self):
        user = User.read(con=self._unpriv, userId="bugsbunny")
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.delete()
        self.assertEqual(str(ex.exception), 'No permission to delete user in project omas:HyperHamlet.')

    # @unittest.skip('Work in progress')
    def test_update_user(self):
        user = User(con=self._connection,
                    userIri=Xsd_anyURI("https://orcid.org/0000-0002-9991-2055"),
                    userId=NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                           AdminPermission.ADMIN_RESOURCES,
                                                           AdminPermission.ADMIN_CREATE}},
                    hasPermissions={QName('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        user2.userId = "aedison"
        user2.familyName = "Edison et al."
        user2.givenName = "Thomas"
        user2.hasPermissions.add(QName('omas:GenericRestricted'))
        user2.hasPermissions.add(QName('omas:HyperHamletMember'))
        user2.hasPermissions.remove(QName('omas:GenericView'))
        user2.inProject[QName('omas:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
        user2.inProject[QName('omas:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
        user2.update()
        user3 = User.read(con=self._connection, userId="aedison")
        self.assertEqual({QName('omas:GenericRestricted'), QName('omas:HyperHamletMember')}, user3.hasPermissions)
        user3.hasPermissions.add(QName('omas:DoesNotExist'))
        with self.assertRaises(OmasErrorValue) as ex:
            user3.update()
            self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')
        self.assertEqual(InProjectClass({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES,
                                                                     AdminPermission.ADMIN_CREATE},
                                         QName('omas:SystemProject'): {AdminPermission.ADMIN_USERS,
                                                                       AdminPermission.ADMIN_RESOURCES}}), user3.inProject)
        del user3
        user4 = User.read(con=self._connection, userId="aedison")
        user4.inProject = InProjectClass({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS}})
        user4.update()
        del user4

    # @unittest.skip('Work in progress')
    def test_update_user_unpriv(self):
        user = User.read(con=self._unpriv, userId="bugsbunny")
        user.credentials = "ChangedPassword"
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.update()
        self.assertEqual(str(ex.exception), 'No permission to modify user in project omas:HyperHamlet.')


if __name__ == '__main__':
    unittest.main()
