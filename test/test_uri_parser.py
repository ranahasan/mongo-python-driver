# Copyright 2011-2015 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the pymongo uri_parser module."""

import copy
import sys
import warnings

sys.path[0:0] = [""]

from pymongo.uri_parser import (_partition,
                                _rpartition,
                                parse_userinfo,
                                split_hosts,
                                split_options,
                                parse_uri)
from pymongo.errors import ConfigurationError, InvalidURI
from pymongo import ReadPreference
from bson.binary import JAVA_LEGACY
from bson.py3compat import string_type, _unicode
from test import unittest


class TestURI(unittest.TestCase):

    def test_partition(self):
        self.assertEqual(('foo', ':', 'bar'), _partition('foo:bar', ':'))
        self.assertEqual(('foobar', '', ''), _partition('foobar', ':'))

    def test_rpartition(self):
        self.assertEqual(('fo:o:', ':', 'bar'), _rpartition('fo:o::bar', ':'))
        self.assertEqual(('', '', 'foobar'), _rpartition('foobar', ':'))

    def test_validate_userinfo(self):
        self.assertRaises(InvalidURI, parse_userinfo,
                          'foo@')
        self.assertRaises(InvalidURI, parse_userinfo,
                          ':password')
        self.assertRaises(InvalidURI, parse_userinfo,
                          'fo::o:p@ssword')
        self.assertRaises(InvalidURI, parse_userinfo, ':')
        self.assertTrue(parse_userinfo('user:password'))
        self.assertEqual(('us:r', 'p@ssword'),
                         parse_userinfo('us%3Ar:p%40ssword'))
        self.assertEqual(('us er', 'p ssword'),
                         parse_userinfo('us+er:p+ssword'))
        self.assertEqual(('us er', 'p ssword'),
                         parse_userinfo('us%20er:p%20ssword'))
        self.assertEqual(('us+er', 'p+ssword'),
                         parse_userinfo('us%2Ber:p%2Bssword'))
        self.assertEqual(('dev1@FOO.COM', ''),
                         parse_userinfo('dev1%40FOO.COM'))
        self.assertEqual(('dev1@FOO.COM', ''),
                         parse_userinfo('dev1%40FOO.COM:'))

    def test_split_hosts(self):
        self.assertRaises(ConfigurationError, split_hosts,
                          'localhost:27017,')
        self.assertRaises(ConfigurationError, split_hosts,
                          ',localhost:27017')
        self.assertRaises(ConfigurationError, split_hosts,
                          'localhost:27017,,localhost:27018')
        self.assertEqual([('localhost', 27017), ('example.com', 27017)],
                         split_hosts('localhost,example.com'))
        self.assertEqual([('localhost', 27018), ('example.com', 27019)],
                         split_hosts('localhost:27018,example.com:27019'))
        self.assertEqual([('/tmp/mongodb-27017.sock', None)],
                         split_hosts('/tmp/mongodb-27017.sock'))
        self.assertEqual([('/tmp/mongodb-27017.sock', None),
                          ('example.com', 27017)],
                         split_hosts('/tmp/mongodb-27017.sock,'
                                     'example.com:27017'))
        self.assertEqual([('example.com', 27017),
                          ('/tmp/mongodb-27017.sock', None)],
                         split_hosts('example.com:27017,'
                                     '/tmp/mongodb-27017.sock'))
        self.assertRaises(ValueError, split_hosts, '::1', 27017)
        self.assertRaises(ValueError, split_hosts, '[::1:27017')
        self.assertRaises(ValueError, split_hosts, '::1')
        self.assertRaises(ValueError, split_hosts, '::1]:27017')
        self.assertEqual([('::1', 27017)], split_hosts('[::1]:27017'))
        self.assertEqual([('::1', 27017)], split_hosts('[::1]'))

    def test_split_options(self):
        self.assertRaises(ConfigurationError, split_options, 'foo')
        self.assertRaises(ConfigurationError, split_options, 'foo=bar;foo')
        self.assertTrue(split_options('ssl=true'))
        self.assertTrue(split_options('connect=true'))
        self.assertTrue(split_options('ssl_match_hostname=true'))

        # Test Invalid URI options that should throw warnings.
        with warnings.catch_warnings():
            warnings.filterwarnings('error')
            self.assertRaises(Warning, split_options,
                              'foo=bar', warn=True)
            self.assertRaises(Warning, split_options,
                              'socketTimeoutMS=foo', warn=True)
            self.assertRaises(Warning, split_options,
                              'socketTimeoutMS=0.0', warn=True)
            self.assertRaises(Warning, split_options,
                              'connectTimeoutMS=foo', warn=True)
            self.assertRaises(Warning, split_options,
                              'connectTimeoutMS=0.0', warn=True)
            self.assertRaises(Warning, split_options,
                              'connectTimeoutMS=1e100000', warn=True)
            self.assertRaises(Warning, split_options,
                              'connectTimeoutMS=-1e100000', warn=True)
            self.assertRaises(Warning, split_options,
                              'ssl=foo', warn=True)
            self.assertRaises(Warning, split_options,
                              'connect=foo', warn=True)
            self.assertRaises(Warning, split_options,
                              'ssl_match_hostname=foo', warn=True)

            # On most platforms float('inf') and float('-inf') represent
            # +/- infinity, although on Python 2.4 and 2.5 on Windows those
            # expressions are invalid
            if not (sys.platform == "win32" and sys.version_info <= (2, 5)):
                self.assertRaises(Warning, split_options,
                                  'connectTimeoutMS=inf', warn=True)
                self.assertRaises(Warning, split_options,
                                  'connectTimeoutMS=-inf', warn=True)

            self.assertRaises(Warning, split_options, 'wtimeoutms=foo',
                              warn=True)
            self.assertRaises(Warning, split_options, 'wtimeoutms=5.5',
                              warn=True)
            self.assertRaises(Warning, split_options, 'fsync=foo',
                              warn=True)
            self.assertRaises(Warning, split_options, 'fsync=5.5',
                              warn=True)
            self.assertRaises(Warning,
                              split_options, 'authMechanism=foo',
                              warn=True)

        # Test invalid options with warn=False.
        self.assertRaises(ConfigurationError, split_options, 'foo=bar')
        self.assertRaises(ValueError, split_options, 'socketTimeoutMS=foo')
        self.assertRaises(ValueError, split_options, 'socketTimeoutMS=0.0')
        self.assertRaises(ValueError, split_options, 'connectTimeoutMS=foo')
        self.assertRaises(ValueError, split_options, 'connectTimeoutMS=0.0')
        self.assertRaises(ValueError, split_options,
                          'connectTimeoutMS=1e100000')
        self.assertRaises(ValueError, split_options,
                          'connectTimeoutMS=-1e100000')
        self.assertRaises(ValueError, split_options, 'ssl=foo')
        self.assertRaises(ValueError, split_options, 'connect=foo')
        self.assertRaises(ValueError, split_options, 'ssl_match_hostname=foo')
        if not (sys.platform == "win32" and sys.version_info <= (2, 5)):
            self.assertRaises(ValueError, split_options,
                              'connectTimeoutMS=inf')
            self.assertRaises(ValueError, split_options,
                              'connectTimeoutMS=-inf')
        self.assertRaises(ValueError, split_options, 'wtimeoutms=foo')
        self.assertRaises(ValueError, split_options, 'wtimeoutms=5.5')
        self.assertRaises(ValueError, split_options, 'fsync=foo')
        self.assertRaises(ValueError, split_options, 'fsync=5.5')
        self.assertRaises(ValueError,
                          split_options, 'authMechanism=foo')

        # Test splitting options works when valid.
        self.assertTrue(split_options('socketTimeoutMS=300'))
        self.assertTrue(split_options('connectTimeoutMS=300'))
        self.assertEqual({'sockettimeoutms': 0.3},
                         split_options('socketTimeoutMS=300'))
        self.assertEqual({'sockettimeoutms': 0.0001},
                         split_options('socketTimeoutMS=0.1'))
        self.assertEqual({'connecttimeoutms': 0.3},
                         split_options('connectTimeoutMS=300'))
        self.assertEqual({'connecttimeoutms': 0.0001},
                         split_options('connectTimeoutMS=0.1'))
        self.assertTrue(split_options('connectTimeoutMS=300'))
        self.assertTrue(isinstance(split_options('w=5')['w'], int))
        self.assertTrue(isinstance(split_options('w=5.5')['w'], string_type))
        self.assertTrue(split_options('w=foo'))
        self.assertTrue(split_options('w=majority'))
        self.assertTrue(split_options('wtimeoutms=500'))
        self.assertEqual({'fsync': True}, split_options('fsync=true'))
        self.assertEqual({'fsync': False}, split_options('fsync=false'))
        self.assertEqual({'authmechanism': 'GSSAPI'},
                         split_options('authMechanism=GSSAPI'))
        self.assertEqual({'authmechanism': 'MONGODB-CR'},
                         split_options('authMechanism=MONGODB-CR'))
        self.assertEqual({'authmechanism': 'SCRAM-SHA-1'},
                         split_options('authMechanism=SCRAM-SHA-1'))
        self.assertEqual({'authsource': 'foobar'},
                         split_options('authSource=foobar'))
        self.assertEqual({'maxpoolsize': 50}, split_options('maxpoolsize=50'))

    def test_parse_uri(self):
        self.assertRaises(InvalidURI, parse_uri, "http://foobar.com")
        self.assertRaises(InvalidURI, parse_uri, "http://foo@foobar.com")
        self.assertRaises(ValueError,
                          parse_uri, "mongodb://::1", 27017)

        orig = {
            'nodelist': [("localhost", 27017)],
            'username': None,
            'password': None,
            'database': None,
            'collection': None,
            'options': {}
        }

        res = copy.deepcopy(orig)
        self.assertEqual(res, parse_uri("mongodb://localhost"))

        res.update({'username': 'fred', 'password': 'foobar'})
        self.assertEqual(res, parse_uri("mongodb://fred:foobar@localhost"))

        res.update({'database': 'baz'})
        self.assertEqual(res, parse_uri("mongodb://fred:foobar@localhost/baz"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("example1.com", 27017), ("example2.com", 27017)]
        self.assertEqual(res,
                         parse_uri("mongodb://example1.com:27017,"
                                   "example2.com:27017"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("localhost", 27017),
                           ("localhost", 27018),
                           ("localhost", 27019)]
        self.assertEqual(res,
                         parse_uri("mongodb://localhost,"
                                   "localhost:27018,localhost:27019"))

        res = copy.deepcopy(orig)
        res['database'] = 'foo'
        self.assertEqual(res, parse_uri("mongodb://localhost/foo"))

        res = copy.deepcopy(orig)
        self.assertEqual(res, parse_uri("mongodb://localhost/"))

        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res, parse_uri("mongodb://"
                                        "localhost/test.yield_historical.in"))

        res.update({'username': 'fred', 'password': 'foobar'})
        self.assertEqual(res,
                         parse_uri("mongodb://fred:foobar@localhost/"
                                   "test.yield_historical.in"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("example1.com", 27017), ("example2.com", 27017)]
        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res,
                         parse_uri("mongodb://example1.com:27017,example2.com"
                                   ":27017/test.yield_historical.in"))

        # Test socket path without escaped characters.
        self.assertRaises(InvalidURI, parse_uri,
                          "mongodb:///tmp/mongodb-27017.sock")

        # Test with escaped characters.
        res = copy.deepcopy(orig)
        res['nodelist'] = [("example2.com", 27017),
                           ("/tmp/mongodb-27017.sock", None)]
        self.assertEqual(res,
                         parse_uri("mongodb://example2.com,"
                                   "%2Ftmp%2Fmongodb-27017.sock"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("shoe.sock.pants.co.uk", 27017),
                           ("/tmp/mongodb-27017.sock", None)]
        res['database'] = "nethers_db"
        self.assertEqual(res,
                         parse_uri("mongodb://shoe.sock.pants.co.uk,"
                                   "%2Ftmp%2Fmongodb-27017.sock/nethers_db"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("/tmp/mongodb-27017.sock", None),
                           ("example2.com", 27017)]
        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res,
                         parse_uri("mongodb://%2Ftmp%2Fmongodb-27017.sock,"
                                   "example2.com:27017"
                                   "/test.yield_historical.in"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("/tmp/mongodb-27017.sock", None),
                           ("example2.com", 27017)]
        res.update({'database': 'test', 'collection': 'yield_historical.sock'})
        self.assertEqual(res,
                         parse_uri("mongodb://%2Ftmp%2Fmongodb-27017.sock,"
                                   "example2.com:27017/test.yield_historical"
                                   ".sock"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("example2.com", 27017)]
        res.update({'database': 'test', 'collection': 'yield_historical.sock'})
        self.assertEqual(res,
                         parse_uri("mongodb://example2.com:27017"
                                   "/test.yield_historical.sock"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("/tmp/mongodb-27017.sock", None)]
        res.update({'database': 'test', 'collection': 'mongodb-27017.sock'})
        self.assertEqual(res,
                         parse_uri("mongodb://%2Ftmp%2Fmongodb-27017.sock"
                                   "/test.mongodb-27017.sock"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [('/tmp/mongodb-27020.sock', None),
                           ("::1", 27017),
                           ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", 27018),
                           ("192.168.0.212", 27019),
                           ("localhost", 27018)]
        self.assertEqual(res, parse_uri("mongodb://%2Ftmp%2Fmongodb-27020.sock"
                                        ",[::1]:27017,[2001:0db8:"
                                        "85a3:0000:0000:8a2e:0370:7334],"
                                        "192.168.0.212:27019,localhost",
                                        27018))

        res = copy.deepcopy(orig)
        res.update({'username': 'fred', 'password': 'foobar'})
        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res,
                         parse_uri("mongodb://fred:foobar@localhost/"
                                   "test.yield_historical.in"))

        res = copy.deepcopy(orig)
        res['database'] = 'test'
        res['collection'] = 'name/with "delimiters'
        self.assertEqual(
            res, parse_uri("mongodb://localhost/test.name/with \"delimiters"))

        res = copy.deepcopy(orig)
        res['options'] = {
            'readpreference': ReadPreference.SECONDARY.mongos_mode
        }
        self.assertEqual(res, parse_uri(
            "mongodb://localhost/?readPreference=secondary"))

        # Various authentication tests
        res = copy.deepcopy(orig)
        res['options'] = {'authmechanism': 'MONGODB-CR'}
        res['username'] = 'user'
        res['password'] = 'password'
        self.assertEqual(res,
                         parse_uri("mongodb://user:password@localhost/"
                                   "?authMechanism=MONGODB-CR"))

        res = copy.deepcopy(orig)
        res['options'] = {'authmechanism': 'MONGODB-CR', 'authsource': 'bar'}
        res['username'] = 'user'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user:password@localhost/foo"
                                   "?authSource=bar;authMechanism=MONGODB-CR"))

        res = copy.deepcopy(orig)
        res['options'] = {'authmechanism': 'MONGODB-CR'}
        res['username'] = 'user'
        res['password'] = ''
        self.assertEqual(res,
                         parse_uri("mongodb://user:@localhost/"
                                   "?authMechanism=MONGODB-CR"))

        res = copy.deepcopy(orig)
        res['username'] = 'user@domain.com'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com:password"
                                   "@localhost/foo"))

        res = copy.deepcopy(orig)
        res['options'] = {'authmechanism': 'GSSAPI'}
        res['username'] = 'user@domain.com'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com:password"
                                   "@localhost/foo?authMechanism=GSSAPI"))

        res = copy.deepcopy(orig)
        res['options'] = {'authmechanism': 'GSSAPI'}
        res['username'] = 'user@domain.com'
        res['password'] = ''
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com"
                                   "@localhost/foo?authMechanism=GSSAPI"))

        res = copy.deepcopy(orig)
        res['options'] = {
            'readpreference': ReadPreference.SECONDARY.mongos_mode,
            'readpreferencetags': [
                {'dc': 'west', 'use': 'website'},
                {'dc': 'east', 'use': 'website'}
            ]
        }
        res['username'] = 'user@domain.com'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com:password"
                                   "@localhost/foo?readpreference=secondary&"
                                   "readpreferencetags=dc:west,use:website&"
                                   "readpreferencetags=dc:east,use:website"))

        res = copy.deepcopy(orig)
        res['options'] = {
            'readpreference': ReadPreference.SECONDARY.mongos_mode,
            'readpreferencetags': [
                {'dc': 'west', 'use': 'website'},
                {'dc': 'east', 'use': 'website'},
                {}
            ]
        }
        res['username'] = 'user@domain.com'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com:password"
                                   "@localhost/foo?readpreference=secondary&"
                                   "readpreferencetags=dc:west,use:website&"
                                   "readpreferencetags=dc:east,use:website&"
                                   "readpreferencetags="))

        res = copy.deepcopy(orig)
        res['options'] = {'uuidrepresentation': JAVA_LEGACY}
        res['username'] = 'user@domain.com'
        res['password'] = 'password'
        res['database'] = 'foo'
        self.assertEqual(res,
                         parse_uri("mongodb://user%40domain.com:password"
                                   "@localhost/foo?uuidrepresentation="
                                   "javaLegacy"))

        with warnings.catch_warnings():
            warnings.filterwarnings('error')
            self.assertRaises(Warning, parse_uri,
                              "mongodb://user%40domain.com:password"
                              "@localhost/foo?uuidrepresentation=notAnOption",
                              warn=True)
        self.assertRaises(ValueError, parse_uri,
                          "mongodb://user%40domain.com:password"
                          "@localhost/foo?uuidrepresentation=notAnOption")

    def test_parse_uri_unicode(self):
        # Ensure parsing a unicode returns option names that can be passed
        # as kwargs. In Python 2.4, keyword argument names must be ASCII.
        # In all Pythons, str is the type of valid keyword arg names.
        res = parse_uri(_unicode("mongodb://localhost/?fsync=true"))
        for key in res['options']:
            self.assertTrue(isinstance(key, str))

    def test_parse_ssl_paths(self):
        # Turn off "validate" since these paths don't exist on filesystem.
        self.assertEqual(
            {'collection': None,
             'database': None,
             'nodelist': [('/MongoDB.sock', None)],
             'options': {'ssl_certfile': '/a/b'},
             'password': 'foo/bar',
             'username': 'jesse'},
            parse_uri(
                'mongodb://jesse:foo%2Fbar@%2FMongoDB.sock/?ssl_certfile=/a/b',
                validate=False))

        self.assertEqual(
            {'collection': None,
             'database': None,
             'nodelist': [('/MongoDB.sock', None)],
             'options': {'ssl_certfile': 'a/b'},
             'password': 'foo/bar',
             'username': 'jesse'},
            parse_uri(
                'mongodb://jesse:foo%2Fbar@%2FMongoDB.sock/?ssl_certfile=a/b',
                validate=False))


if __name__ == "__main__":
    unittest.main()
