import gc
import inspect

from cherrypy import _cprequest


class ReferrerTree(object):
    """An object which gathers all referrers of an object to a given depth."""

    peek_length = 40

    def __init__(self, ignore=None, maxdepth=2, maxparents=10):
        self.ignore = ignore or []
        self.ignore.append(inspect.currentframe().f_back)
        self.maxdepth = maxdepth
        self.maxparents = maxparents

    def ascend(self, obj, depth=1):
        """Return a nested list containing referrers of the given object."""
        depth += 1
        parents = []

        # Gather all referrers in one step to minimize
        # cascading references due to repr() logic.
        refs = gc.get_referrers(obj)
        self.ignore.append(refs)
        if len(refs) > self.maxparents:
            return [("[%s referrers]" % len(refs), [])]

        try:
            ascendcode = self.ascend.__code__
        except AttributeError:
            ascendcode = self.ascend.im_func.func_code
        for parent in refs:
            if inspect.isframe(parent) and parent.f_code is ascendcode:
                continue
            if parent in self.ignore:
                continue
            if depth <= self.maxdepth:
                parents.append((parent, self.ascend(parent, depth)))
            else:
                parents.append((parent, []))

        return parents

    def peek(self, s):
        """Return s, restricted to a sane length."""
        if len(s) > (self.peek_length + 3):
            half = self.peek_length // 2
            return s[:half] + '...' + s[-half:]
        else:
            return s

    def _format(self, obj, descend=True):
        """Return a string representation of a single object."""
        if inspect.isframe(obj):
            filename, lineno, func, context, index = inspect.getframeinfo(obj)
            return "<frame of function '%s'>" % func

        if not descend:
            return self.peek(repr(obj))

        if isinstance(obj, dict):
            return "{" + ", ".join(["%s: %s" % (self._format(k, descend=False),
                                                self._format(v, descend=False))
                                    for k, v in obj.items()]) + "}"
        elif isinstance(obj, list):
            return "[" + ", ".join([self._format(item, descend=False)
                                    for item in obj]) + "]"
        elif isinstance(obj, tuple):
            return "(" + ", ".join([self._format(item, descend=False)
                                    for item in obj]) + ")"

        r = self.peek(repr(obj))
        if isinstance(obj, (str, int, float)):
            return r
        return "%s: %s" % (type(obj), r)

    def format(self, tree):
        """Return a list of string reprs from a nested list of referrers."""
        output = []
        def ascend(branch, depth=1):
            for parent, grandparents in branch:
                output.append(("    " * depth) + self._format(parent))
                if grandparents:
                    ascend(grandparents, depth + 1)
        ascend(tree)
        return output


def get_instances(cls):
    return [x for x in gc.get_objects() if isinstance(x, cls)]


class GCRoot(object):
    """A CherryPy page handler for testing reference leaks."""

    classes = [(_cprequest.Request, 2, 2,
                "Should be 1 in this request thread and 1 in the main thread."),
               (_cprequest.Response, 2, 2,
                "Should be 1 in this request thread and 1 in the main thread."),
               ]

    def index(self):
        return "Hello, world!"
    index.exposed = True

    def stats(self):
        output = ["Statistics:"]
        
        # gc_collect isn't perfectly synchronous, because it may
        # break reference cycles that then take time to fully
        # finalize. Call it thrice and hope for the best.
        gc.collect()
        gc.collect()
        unreachable = gc.collect()
        if unreachable:
            output.append("\n%s unreachable objects:" % unreachable)
            trash = {}
            for x in gc.garbage:
                trash[type(x)] = trash.get(type(x), 0) + 1
            trash = [(v, k) for k, v in trash.items()]
            trash.sort()
            for pair in trash:
                output.append("    " + repr(pair))
        
        # Check declared classes to verify uncollected instances.
        # These don't have to be part of a cycle; they can be
        # any objects that have unanticipated referrers that keep
        # them from being collected.
        for cls, minobj, maxobj, msg in self.classes:
            objs = get_instances(cls)
            lenobj = len(objs)
            if lenobj < minobj or lenobj > maxobj:
                if minobj == maxobj:
                    output.append(
                        "\nExpected %s %r references, got %s." %
                        (minobj, cls, lenobj))
                else:
                    output.append(
                        "\nExpected %s to %s %r references, got %s." %
                        (minobj, maxobj, cls, lenobj))
                for obj in objs:
                    output.append("\nReferrers for %s:" % repr(obj))
                    t = ReferrerTree(ignore=[objs], maxdepth=3)
                    tree = t.ascend(obj)
                    output.extend(t.format(tree))
        
        return "\n".join(output)
    stats.exposed = True

