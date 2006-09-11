import md5
import cherrypy

from httpauth import parseAuthorization, checkResponse, basicAuth, digestAuth


def check_auth(users, encrypt=None):
    """If an authorization header contains credentials, return True, else False."""
    if 'authorization' in cherrypy.request.headers:
        # make sure the provided credentials are correctly set
        ah = parseAuthorization(cherrypy.request.headers['authorization'])
        if ah is None:
            raise cherrypy.HTTPError(400, 'Bad Request')

        if not encrypt:
            encrypt = lambda x: md5.new(x).hexdigest()

        if callable(users):
            users = users() # expect it to return a dictionary

        if not isinstance(users, dict):
            raise ValueError, "Authentication users must be passed contained in a dictionary"
    
        # fetch the user password
        password = users.get(ah["username"], None)
        
        # validate the authorization by re-computing it here
        # and compare it with what the user-agent provided
        if checkResponse(ah, password, method=cherrypy.request.method, encrypt=encrypt):
            return True
    
    return False

def basic_auth(realm, users, encrypt=None):
    """If auth fails, raise 401 with a basic authentication header.
    
    realm: a string containing the authentication realm.
    users: a dict of the form: {username: password} or a callable returning a dict.
    encrypt: callable used to encrypt the password returned from the user-agent.
             if None it defaults to a md5 encryption.
    """
    if check_auth(users, encrypt):
        return
    
    # inform the user-agent this path is protected
    cherrypy.response.headers['www-authenticate'] = basicAuth(realm)
    
    raise cherrypy.HTTPError(401, "You are not authorized to access that resource") 

def digest_auth(realm, users):
    """If auth fails, raise 401 with a digest authentication header.
    
    realm: a string containing the authentication realm.
    users: a dict of the form: {username: password} or a callable returning a dict.
    """
    if check_auth(users):
        return
    
    # inform the user-agent this path is protected
    cherrypy.response.headers['www-authenticate'] = digestAuth(realm)
    
    raise cherrypy.HTTPError(401, "You are not authorized to access that resource") 
 
