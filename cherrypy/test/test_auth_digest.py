# This file is part of CherryPy <http://www.cherrypy.org/>
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:expandtab:fileencoding=utf-8


import cherrypy
from cherrypy.lib import auth_digest
from cherrypy._cpcompat import ntob

from cherrypy.test import helper

from six.moves.urllib.parse import quote as urlencode


def _fetch_users():
    return {'test': 'test', 'йюзер': 'їпароль'}


get_ha1 = cherrypy.lib.auth_digest.get_ha1_dict_plain(_fetch_users())


class DigestAuthTest(helper.CPWebCase):

    @staticmethod
    def setup_server():
        class Root:

            @cherrypy.expose
            def index(self):
                return 'This is public.'

        class DigestProtected:

            @cherrypy.expose
            def index(self):
                return "Hello %s, you've been authorized." % (
                    cherrypy.request.login)

        conf = {'/digest': {'tools.auth_digest.on': True,
                            'tools.auth_digest.realm': 'localhost',
                            'tools.auth_digest.get_ha1': get_ha1,
                            'tools.auth_digest.key': 'a565c27146791cfb',
                            'tools.auth_digest.debug': True,
                            'tools.auth_digest.accept_charset': 'UTF-8'}}

        root = Root()
        root.digest = DigestProtected()
        cherrypy.tree.mount(root, config=conf)

    def testPublic(self):
        self.getPage('/')
        assert self.status == '200 OK'
        self.assertHeader('Content-Type', 'text/html;charset=utf-8')
        assert self.body == b'This is public.'

    def testDigest(self):
        self.getPage('/digest/')
        assert self.status_code == 401


        www_auth_digest = tuple(filter(
            lambda kv: kv[0].lower() == 'www-authenticate'
            and kv[1].startswith('Digest '),
            self.headers,
        ))
        assert len(www_auth_digest) == 1, 'Digest authentification scheme was not found'

        items = www_auth_digest[0][-1][7:].split(', ')
        tokens = {}
        for item in items:
            key, value = item.split('=')
            tokens[key.lower()] = value

        missing_msg = '%s is missing'
        bad_value_msg = "'%s' was expecting '%s' but found '%s'"
        nonce = None
        assert 'realm' in tokens, missing_msg % 'realm'
        assert tokens['realm'] == '"localhost"', bad_value_msg % (
            'realm', '"localhost"', tokens['realm'],
        )
        assert 'nonce' in tokens, missing_msg % 'nonce'
        nonce = tokens['nonce'].strip('"')
        assert 'algorithm' in tokens, missing_msg % 'algorithm'
        assert tokens['algorithm'] == '"MD5"', bad_value_msg % (
            'algorithm', '"MD5"', tokens['algorithm'],
        )
        assert 'qop' in tokens, missing_msg % 'qop'
        assert tokens['qop'] == '"auth"', bad_value_msg % (
            'qop', '"auth"', tokens['qop'],
        )

        # Test user agent response with a wrong value for 'realm'
        base_auth = ('Digest username="test", '
                     'realm="wrong realm", '
                     'nonce="%s", '
                     'uri="/digest/", '
                     'algorithm=MD5, '
                     'response="%s", '
                     'qop=auth, '
                     'nc=%s, '
                     'cnonce="1522e61005789929"')

        auth_header = base_auth % (
            nonce, '11111111111111111111111111111111', '00000001')
        auth = auth_digest.HttpDigestAuthorization(auth_header, 'GET')
        # calculate the response digest
        ha1 = get_ha1(auth.realm, 'test')
        response = auth.request_digest(ha1)
        # send response with correct response digest, but wrong realm
        auth_header = base_auth % (nonce, response, '00000001')
        self.getPage('/digest/', [('Authorization', auth_header)])
        assert self.status_code == 401
        www_auth_unicode = tuple(filter(
            lambda kv: kv[0].lower() == 'www-authenticate'
            and kv[1].endswith(', charset="UTF-8"'),
            self.headers,
        ))
        assert len(www_auth_unicode) == 1

        # Test that must pass
        base_auth = ('Digest username="test", '
                     'realm="localhost", '
                     'nonce="%s", '
                     'uri="/digest/", '
                     'algorithm=MD5, '
                     'response="%s", '
                     'qop=auth, '
                     'nc=%s, '
                     'cnonce="1522e61005789929"')

        auth_header = base_auth % (
            nonce, '11111111111111111111111111111111', '00000001')
        auth = auth_digest.HttpDigestAuthorization(auth_header, 'GET')
        # calculate the response digest
        ha1 = get_ha1(auth.realm, 'test')
        response = auth.request_digest(ha1)
        # send response with correct response digest
        auth_header = base_auth % (nonce, response, '00000001')
        self.getPage('/digest/', [('Authorization', auth_header)])
        assert self.status == '200 OK'
        assert self.body == b"Hello test, you've been authorized."

        # Test with unicode username that must pass
        base_auth = ('Digest username="%s", '
                     'realm="localhost", '
                     'nonce="%s", '
                     'uri="/digest/", '
                     'algorithm=MD5, '
                     'response="%s", '
                     'qop=auth, '
                     'nc=%s, '
                     'cnonce="1522e61005789929"')

        encoded_user = urlencode('йюзер', 'utf-8')
        auth_header = base_auth % (
            encoded_user, nonce,
            '11111111111111111111111111111111', '00000001',
        )
        auth = auth_digest.HttpDigestAuthorization(auth_header, 'GET')
        # calculate the response digest
        ha1 = get_ha1(auth.realm, 'йюзер')
        response = auth.request_digest(ha1)
        # send response with correct response digest
        auth_header = base_auth % (encoded_user, nonce, response, '00000001')
        self.getPage('/digest/', [('Authorization', auth_header)])
        assert self.status == '200 OK'
        assert self.body == ntob("Hello йюзер, you've been authorized.", 'utf-8')
