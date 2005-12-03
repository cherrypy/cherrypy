import time

try:
    import cPickle as pickle
except ImportError:
    import pickle

import cherrypy
from basefilter import BaseFilter


class LogDebugInfoFilter(BaseFilter):
    """Filter that adds debug information to the page"""
    
    def on_start_resource(self):
        cherrypy.request.startBuilTime = time.time()
    
    def before_finalize(self):
        if not cherrypy.config.get('log_debug_info_filter.on', False):
            return
        
        mimelist = cherrypy.config.get('log_debug_info_filter.mime_types', ['text/html'])
        ct = cherrypy.response.headers.get('Content-Type').split(';')[0]
        if ct in mimelist:
            body = cherrypy.response.collapse_body()
            debuginfo = '\n'
            
            logAsComment = cherrypy.config.get('log_debug_info_filter.log_as_comment', False)
            if logAsComment:
                debuginfo += '<!-- '
            else:
                debuginfo += "<br/><br/>"
            logList = []
            
            if cherrypy.config.get('log_debug_info_filter.log_build_time', True):
                logList.append("Build time: %.03fs" % (
                    time.time() - cherrypy.request.startBuilTime))
            
            if cherrypy.config.get('log_debug_info_filter.log_page_size', True):
                logList.append("Page size: %.02fKB" % (
                    len(body)/float(1024)))
            ''' 
            # this is not compatible with the session filter
            if (cherrypy.config.get('log_debug_info_filter.log_session_size', True)
                and cherrypy.config.get('session.storageType')):
                # Pickle session data to get its size
                try:
                    dumpStr = pickle.dumps(cherrypy.request.sessionMap, 1)
                    logList.append("Session data size: %.02fKB" %
                                   (len(dumpStr) / float(1024)))
                except:
                    logList.append("Session data size: Unable to pickle session")
            '''
            
            debuginfo += ', '.join(logList)
            if logAsComment:
                debuginfo += '-->'
            
            cherrypy.response.body = [body, debuginfo]
