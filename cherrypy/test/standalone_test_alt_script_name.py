import test
test.prefer_parent_path()

import cherrypy
from cherrypy._cpwsgi import wsgiApp, WSGIServer

class Root:
    def index(self, name="world"):
        return name
    index.exposed = True
    
    def default(self, *params):
        return "default:"+repr(params)
    default.exposed = True
    
    def other(self):
        return "other"
    other.exposed = True
    
    def extra(self, *p):
        return repr(p)
    extra.exposed = True
    
    def redirect(self):
        raise cherrypy.HTTPRedirect('dir1/', 302)
    redirect.exposed = True
    
    def notExposed(self):
        return "not exposed"
    
    def confvalue(self):
        return cherrypy.config.get("user")
    confvalue.exposed = True

    def script_name(self):
        env = getattr(cherrypy.request, 'wsgi_environ', {})
        sn = env.get('SCRIPT_NAME', '*MISSING*')
        return sn
    script_name.exposed = True
            

def mapped_func(self, ID=None):
    return "ID is %s" % ID
mapped_func.exposed = True
setattr(Root, "Von B\xfclow", mapped_func)


class Exposing:
    def base(self):
        return "expose works!"
    cherrypy.expose(base)
    cherrypy.expose(base, "1")
    cherrypy.expose(base, "2")

class ExposingNewStyle(object):
    def base(self):
        return "expose works!"
    cherrypy.expose(base)
    cherrypy.expose(base, "1")
    cherrypy.expose(base, "2")



class Dir1:
    def index(self):
        return "index for dir1"
    index.exposed = True
    
    def myMethod(self):
        return "myMethod from dir1, object Path is:" + repr(cherrypy.request.object_path)
    myMethod.exposed = True
    
    def default(self, *params):
        return "default for dir1, param is:" + repr(params)
    default.exposed = True


class Dir2:
    def index(self):
        return "index for dir2, path is:" + cherrypy.request.path
    index.exposed = True
    
    def mount_point(self):
        return cherrypy.tree.mount_point()
    mount_point.exposed = True
    
    def tree_url(self):
        return cherrypy.tree.url("/extra")
    tree_url.exposed = True
    
    def posparam(self, *vpath):
        return "/".join(vpath)
    posparam.exposed = True


class Dir3:
    def default(self):
        return "default for dir3, not exposed"


class Dir4:
    def index(self):
        return "index for dir4, not exposed"

Root.exposing = Exposing()
Root.exposingnew = ExposingNewStyle()
Root.dir1 = Dir1()
Root.dir1.dir2 = Dir2()
Root.dir1.dir2.dir3 = Dir3()
Root.dir1.dir2.dir3.dir4 = Dir4()

mount_points = ["/apps", "/apps/users/fred/blog", "/apps/corp/blog"]
for url in mount_points:
    conf = {'user': url.split("/")[-2]}
    cherrypy.tree.mount(Root(), url, {'/': conf})

cherrypy.config.update({
    'server.log_to_screen': False,
    'server.environment': "production",
})


class Isolated:
    def index(self):
        return "made it!"
    index.exposed = True

cherrypy.tree.mount(Isolated(), "/apps/isolated")

# dispatch code courtesy of Ian Bicking
# (posted on the python WEB-SIG ml)
def dispatch(app_map):
    app_map = app_map.items()
    app_map.sort(lambda a, b: -cmp(len(a[0]), len(b[0])))
    def application(environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        for app_prefix, app in app_map:
            app_prefix = app_prefix.rstrip('/')+'/'
            if path_info.startswith(app_prefix):
                environ['SCRIPT_NAME'] += app_prefix[:-1]
                environ['PATH_INFO'] = environ.get(
                    'PATH_INFO', '')[len(app_prefix)-1:]
                return app(environ, start_response)
            else:
                start_response('404 Not Found', [])
                return []
    return application

mp = '/apps'

dispatching_app = dispatch({
  mp: wsgiApp,
  }) 

cherrypy.server.wsgi_app = dispatching_app

import helper

class ObjectMappingTest(helper.CPWebCase):
    
    def testWSGIMountPoint(self):
        self.getPage('/missing')
        self.assertStatus('404 Not Found')

        self.mount_point = mp
        self.getPage('/script_name')
        self.assertBody(mp)

    def testObjectMapping(self):
        for url in mount_points:
            prefix = self.mount_point = url
            if prefix == "/":
                prefix = ""
            
            self.getPage('/')
            self.assertBody('world')
            
            self.getPage("/dir1/myMethod")
            self.assertBody("myMethod from dir1, object Path is:'%s/dir1/myMethod'"
                            % prefix)
            
            self.getPage("/this/method/does/not/exist")
            self.assertBody("default:('this', 'method', 'does', 'not', 'exist')")
            
            self.getPage("/extra/too/much")
            self.assertBody("('too', 'much')")
            
            self.getPage("/other")
            self.assertBody('other')
            
            self.getPage("/notExposed")
            self.assertBody("default:('notExposed',)")
            
            self.getPage("/dir1/dir2/")
            self.assertBody('index for dir2, path is:%s/dir1/dir2/'
                            % prefix)
            
            self.getPage("/dir1/dir2")
            self.assert_(self.status in ('302 Found', '303 See Other'))
            self.assertHeader('Location', 'http://%s:%s%s/dir1/dir2/'
                              % (self.HOST, self.PORT, prefix))
            
            self.getPage("/dir1/dir2/dir3/dir4/index")
            self.assertBody("default for dir1, param is:('dir2', 'dir3', 'dir4', 'index')")
            
            self.getPage("/redirect")
            self.assertStatus('302 Found')
            self.assertHeader('Location', 'http://%s:%s%s/dir1/'
                              % (self.HOST, self.PORT, prefix))
            
            # Test that we can use URL's which aren't all valid Python identifiers
            # This should also test the %XX-unquoting of URL's.
            self.getPage("/Von%20B%fclow?ID=14")
            self.assertBody("ID is 14")
            
            # Test that %2F in the path doesn't get unquoted too early;
            # that is, it should not be used to separate path components.
            # See ticket #393.
            self.getPage("/page%2Fname")
            self.assertBody("default:('page/name',)")
            
            self.getPage("/dir1/dir2/mount_point")
            self.assertBody(url)
            self.getPage("/dir1/dir2/tree_url")
            self.assertBody(prefix + "/extra")
            
            # Test that configs don't overwrite each other from diferent apps
            self.getPage("/confvalue")
            self.assertBody(url.split("/")[-2])
        
        self.mount_point = mp
        
        # Test that the "isolated" app doesn't leak url's into the root app.
        # If it did leak, Root.default() would answer with
        #   "default:('isolated', 'doesnt', 'exist')".
        self.getPage("/isolated/")
        self.assertStatus("200 OK")
        self.assertBody("made it!")
        self.getPage("/isolated/doesnt/exist")
        self.assertStatus("404 Not Found")
    
    def testPositionalParams(self):
        self.mount_point = mp

        self.getPage("/dir1/dir2/posparam/18/24/hut/hike")
        self.assertBody("18/24/hut/hike")
        
        # intermediate index methods should not receive posparams;
        # only the "final" index method should do so.
        self.getPage("/dir1/dir2/5/3/sir")
        self.assertBody("default for dir1, param is:('dir2', '5', '3', 'sir')")
    
    def testExpose(self):
        self.mount_point = mp
        
        # Test the cherrypy.expose function/decorator
        self.getPage("/exposing/base")
        self.assertBody("expose works!")
        
        self.getPage("/exposing/1")
        self.assertBody("expose works!")
        
        self.getPage("/exposing/2")
        self.assertBody("expose works!")
        
        self.getPage("/exposingnew/base")
        self.assertBody("expose works!")
        
        self.getPage("/exposingnew/1")
        self.assertBody("expose works!")
        
        self.getPage("/exposingnew/2")
        self.assertBody("expose works!")



if __name__ == "__main__":
    helper.testmain(WSGIServer)
