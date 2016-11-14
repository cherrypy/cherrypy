import cherrypy

# from services.userServiceProvider import UserServiceProvider

from typing import Dict, List

'''
NOTES
 + @cherrypy.tools.json_out() - automatically outputs response in JSON
 + @cherrypy.tools.json_in()  - automatically parses JSON body
'''
class UserController():

    # expose all the class methods at once
    exposed = True
    
    def __init__(self):
        # create an instance of the service provider
        # self.userService = UserServiceProvider()
        pass

    '''
    This code allows for our routes to look like http://example.com/api/users/uuid
    and the uuid will be made available to the routes like the user input
    http://example.com/api/users?uuid=uuid
    ''' 
    def _cp_dispatch(self, vpath: List[str]):
        
        # since our routes will only contain the GUID, we'll only have 1 
        # path. If we have more, just ignore it
        if len(vpath) == 1:
            cherrypy.request.params['uuid'] = vpath.pop()
        
        return self

    @cherrypy.tools.json_out()
    def GET(self, **kwargs: Dict[str, str]) -> str:
        """
        Either gets all the users or a particular user if ID was passed in.
        By using the cherrypy tools decorator we can automagically output JSON
        without having to using json.dumps()
        """

        # our URI should be /api/users/{GUID}, by using _cp_dispatch, this 
        # changes the URI to look like /api/users?uuid={GUID}
        
        if 'uuid' not in kwargs:
            # if no GUID was passed in the URI, we should get all users' info
            # from the database
            # results =  self.userService.getAllUsers()
            results = {
                'status' : 'getting all users'
            }
        else:
            # results = self.userService.getUser(kwargs['uuid'])
            results = {
                'status' : 'searching for user ' + kwargs['uuid']
            }

        return results
    
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        """Creates a new user
        """
        input = cherrypy.request.json
        inputParams = {}
        
        # convert the keys from unicode to regular strings
        for key, value in input.items():
           inputParams[key] = str(value)
        
        try:
            # result = self.userService.addUser(inputParams)
            result = {
                'status' : 'inserting new record'
            }

            if len(inputParams) == 0:
                raise Exception('no body')
        except Exception as err:
            result = {'error' : 'Failed to create user. ' + err.__str__()}

        return result
    
    @cherrypy.tools.json_out()
    def DELETE(self, **kwargs: Dict[str, str]):
        # convert the keys from unicode to regular strings
        uuid = ''
        if 'uuid' not in kwargs:
            result = {
                'success' : False,
                'message' : 'You must specfy a user.'
            }

            return result

        uuid = kwargs['uuid']

        try:
            if len(uuid) == 0:
                raise Exception('must pass in user ID')
            
            # result = self.userService.deleteUser(inputParams)
            result = {
                'status' : 'deleting user with ID: ' + uuid
            }
        except Exception as err:
            result = {'error' : 'could not delete. ' + err.__str__()}

        return result

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self):
        # get the request body
        data = cherrypy.request.json
        print('BODY:\n' + str(data))
        # result = self.userService.updateUser(data)
        result = {
            'status' : 'updating user'
        }

        return result

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PATCH(self, **kwargs: Dict[str, str]):

        # the _cp_dispatch() method
        if 'uuid' not in kwargs:
            result = {
                'success' : False,
                'message' : 'You must specfy a user.'
            }

            return result
        else:
            print('found uuid: ' + kwargs['uuid'])

        # get the request body
        data = cherrypy.request.json

        print('HTTP BODY: ' + str(data))
        
        # result = self.userService.updateUser(data, kwargs['uuid'])
        result = {
            'status' : 'patching user ({})'.format(kwargs['uuid'])
        }

        return result

    def OPTIONS(self):
        return 'Allow: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT'

    def HEAD(self):
        return ''

