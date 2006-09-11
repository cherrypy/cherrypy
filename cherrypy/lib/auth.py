
import cherrypy
from cherrypy._cptools import Tool 

from httpauth import parseAuthorization, checkResponse, basicAuth, digestAuth

def check_auth(realm, users):
    # Check if the user-agent provides an authorization header
    # containing credentials
    if 'authorization' in cherrypy.request.headers:
        # make sure the provided credentials are correctly set
        ah = parseAuthorization(cherrypy.request.headers['authorization'])
        if ah is None:
            raise cherrypy.HTTPError(400, 'Bad Request')
 
        # fetch the user password
        password = users.get(ah["username"], None)
 
        # validate the authorization by re-computing it here
        # and compare it with what the user-agent provided
        if checkResponse(ah, password, method=cherrypy.request.method):
            return True
        
    return False
 
def basic_auth(realm, users):
    if check_auth(realm, users):
        return
    
    # inform the user-agent this path is protected
    cherrypy.response.headers['www-authenticate'] = basicAuth(realm)
    
    raise cherrypy.HTTPError(401, "You are not authorized to access that resource") 
 
def digest_auth(realm, users):
    if check_auth(realm, users):
        return
    
    # inform the user-agent this path is protected
    cherrypy.response.headers['www-authenticate'] = digestAuth(realm)
    
    raise cherrypy.HTTPError(401, "You are not authorized to access that resource") 
 
