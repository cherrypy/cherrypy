"""
_cpmagicattr.py

Implements the magic attributes interface, as described in:
http://www.cherrypy.org/wiki/FastMagicAttributeLookup
"""

import cpg

# binds the config to internal names. this is required to allow unit
# testing; we simply put test values here instead of the defaults.

configMap = cpg.configMap
defaultConfigMap = cpg.defaultConfigMap
cpgTree = cpg
reservedAttrNames = ['configMap','defaultConfigMap']

#-------------------------------------------------------------------------
# DEFAULT DICTIONARY HANDLING

def setDefaultAttr(section, attr, value):
    """
    Sets a default value for a section/attribute
    
    Example:
        setDefaultAttr('root', 'encodingFilter', 'on')
        setDefaultAttr('root', 'encodingFilter.encoding', 'utf8')
    """
    sectMap = defaultConfigMap.setdefault(section, {})
    sectMap[attr] = value

def setDefaultMap(section, map):
    """
    Sets many default values for a section.
    
    Example:
        setDefaultMap('root', 
            {'encodingFilter':'on', 'encodingFilter.encoding':'utf8')
    """
    sectMap = defaultConfigMap.setdefault(section, {})
    sectMap.update(map)

#-------------------------------------------------------------------------
# SYSTEM-WIDE CPG OBJECT CACHE

class CpgObjCache:
    """
    Cache of objects attached to the CPG tree. Provides fast access to 
    the objects in the tree, using the cpgpath for direct lookup.
    """
    
    def __init__(self):
        self.cache = {}
        
    def __getitem__(self, cpgpath):
        try:
            cpgobj = self.cache[cpgpath]
        except KeyError:
            # loop over the cpg tree searching for the object
            cpgobj = cpgTree
            for item in cpgpath.split('.'):
                try:
                    cpgobj = getattr(cpgobj, item)
                except AttributeError:
                    raise KeyError
            self.cache[cpgpath] = cpgobj
        return cpgobj
        
cpgObjCache = CpgObjCache()

#-------------------------------------------------------------------------
# SYSTEM-WIDE ATTRIBUTE CACHE

class MagicAttrCache:
    """
    Implements a dictionary-like cache of MagicAttrDicts. The index key
    is the 'cpgpath', as a string.

    Implementation note: for now, this class is nothing more than a 
    simple wrapper around the cache dict. We will put more stuff here
    as the code evolves (cache expiration, etc).
    """

    def __init__(self):
        self.cache = {}
        
    def __getitem__(self, key):
        return self.cache[key]
        
    def __setitem__(self, key, value):
        self.cache[key] = value
    
magicAttrCache = MagicAttrCache()

#-------------------------------------------------------------------------
# MAGIC ATTRIBUTE LOOKUP CLASS

class MagicAttrDict(object):
    
    def __init__(self, cpgpath):
        self.cpgpath = cpgpath
        self.attrCache = {}
        self.parent = cpgpath[:cpgpath.rfind('.')]

    def __repr__(self):
        return "<MagicAttrDict: %r, %r>" % (self.cpgpath, self.attrCache)

    def __getitem__(self, attrname):
        # returns the attribute for the particular section
        try:
            attrinfo = self.attrCache[attrname]
        except KeyError:
            # not cached, search for the value
            attrinfo = self.search(attrname)
            self.attrCache[attrname] = attrinfo
        return attrinfo

    def search_bottom_up(self, attrname):
        """
        Search on configMap, defaultConfigMap, and cpgTree simultaneously
        Potentially recursive bottom-up implementation. It is fast 
        because it can take advantage of the cache, but it it can't
        detect the correct type for a config value because it doesnt
        stops before reaching the default value.
        """
        try:
            try:
                sectionMap = configMap[self.cpgpath]
            except KeyError:
                try:
                    cpgobj = cpgObjCache[self.cpgpath]
                    value = getattr(cpgobj, attrname)
                    return value
                except (KeyError, AttributeError):
                    sectionMap = defaultConfigMap[self.cpgpath]
            return sectionMap[attrname]
        except KeyError:
            return MagicAttrDict(self.parent)[attrname]

    def search_top_down(self, attrname, lookupCpgTree=False):
        """
        Search on configMap, defaultConfigMap, and cpgTree simultaneously
        Iterative top-down version. Probably slower than the bottom
        up version for big & deep web sites, because it never caches 
        values during the traversal; on the other hand, as it starts
        on the top of the tree, it can detect the correct type of
        the attribute by checking the default value. It also can 
        be configured to ignore the cpg tree during the search.
        """
        cpgobj = cpgTree
        partialPath = ''
        lastDefaultType = str
        for item in self.cpgpath.split('.'):
            # check the default value for ths level of the tree
            partialPath = partialPath + item
            try:
                sectionMap = defaultConfigMap[partialPath]
                curvalue = sectionMap[attrname]
                lastDefaultType = type(curvalue)
            except KeyError:
                pass
            # check the attributes (only if asked to!)
            if lookupCpgTree:
                try:
                    cpgobj = getattr(cpgobj, item)
                    curvalue = getattr(cpgobj, attrname, curvalue)
                except AttributeError:
                    # Unreachable node. Stops looking for attributes
                    lookupCpgTree = False
            # check the configuration map
            try:
                sectionMap = configMap[partialPath]
                curvalue = sectionMap[attrname]
            except KeyError:
                pass
            partialPath = partialPath + '.'
        # found all intermediate values, 
        if isinstance(curvalue, basestring):
            return lastDefaultType(curvalue)
        else:
            return curvalue
        
    search = search_top_down

    def getStaticDict(self):
        """
        Special case for the staticContent session. It should return a dict, 
        directly from the configMap.
        """
        return configMap.setdefault(self.cpgpath, {})
        
def MagicAttrDict(cpgpath, cached=True, MagicClass=MagicAttrDict):
    """
    Simple wrapper around the MagicAttrDict, implements the caching.
    Avoids a lot of worries with __new__ & __init__. Believe me, 
    they're hard to use properly.
    """
    # looks in the cache if possible
    if cached:
        try:
            obj = magicAttrCache[cpgpath]
            return obj
        except KeyError:
            pass
    # not cached, create a new instance
    obj = MagicClass(cpgpath)
    magicAttrCache[cpgpath] = obj
    return obj

#-------------------------------------------------------------------------

def getConfig(section, attrname=None):
    if attrname:
        return MagicAttrDict(section)[attrname]
    else:
        return MagicAttrDict(section).getStaticDict()

cpg.getConfig = getConfig

#-------------------------------------------------------------------------

testConfigText = """
[root]
encodingFilter = on
encodingFilter.encoding = latin1
cacheFilter = on
cacheFilter.timeout = 60

[root.wiki]
encodingFilter.encoding = utf8
cacheFilter.timeout = 30
gzipFilter = off
""" 
    
def test():
    """simple testing"""
    testDefaultConfigMap = {
        'server': {
            'logFile': '',
            },
        'root': {
            'encodingFilter':'on',
            'encodingFilter.encoding':'utf8',
            },
        }
    
    class TestCpgTree: pass
    class TestRoot: pass
    class TestWiki: pass
        
    testCpgTree = TestCpgTree()
    testCpgTree.root = TestRoot()
    testCpgTree.root.wiki = TestWiki()
    testCpgTree.root.wiki.gzipFilter = 'off' 
    # set default test values
    import StringIO
    testConfigFile = StringIO.StringIO(testConfigText)
    configMap = {}
    defaultConfigMap = testDefaultConfigMap
    cpgTree = testCpgTree
    reservedAttrNames = ['configMap','defaultConfigMap']
    # register more default values (simulates filters)
    setDefaultMap(
        'root', {'encodingFilter':'on', 'encodingFilter.encoding':'utf8'}
        )
    setDefaultMap(
        'root', {'cacheFilter':'off', 'cacheFilter.timeout':600}
        )
    setDefaultAttr('root', 'gzipFilter', 'on')
    # access some attributes & check the values
    print "-"*80
    ma = MagicAttrDict('root')
    print "Before access:", ma
    assert ma['encodingFilter'] =='on'
    assert ma['encodingFilter.encoding'] =='latin1'
    assert ma['cacheFilter'] =='on'
    assert ma['cacheFilter.timeout'] == 60
    assert ma['gzipFilter'] == 'on'
    print "After access:", ma
    print "-"*80
    ma = MagicAttrDict('root.wiki')
    print "Before access:", ma
    assert ma['encodingFilter'] == 'on'
    assert ma['encodingFilter.encoding'] == 'utf8'
    assert ma['cacheFilter'] == 'on'
    assert ma['cacheFilter.timeout'] == 30
    assert ma['gzipFilter'] == 'off'
    print "After access:", ma

    def timeMagicAttr(cached, msg):
        print "-"*80
        print msg
        import time
        startTime = time.time()
        for i in range(10000):
            ma = MagicAttrDict('root.wiki', cached=cached)
            assert ma['encodingFilter'] == 'on'
            assert ma['encodingFilter.encoding'] == 'utf8'
            assert ma['cacheFilter'] == 'on'
            assert ma['cacheFilter.timeout'] == 30
            assert ma['gzipFilter'] == 'off'
        elapsedTime = time.time()-startTime
        print "Total time (10000 accesses for 5 attributes): %1.3fs, %1.3f ms per loop" % (elapsedTime, elapsedTime/50)

    timeMagicAttr(True, "Timing: cache activated")
    timeMagicAttr(False, "Timing: cache deactivated")
    
if __name__ == '__main__':
    test()
