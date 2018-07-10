from jaraco.packaging import depends



def test_dependencies_no_namespaces():
    """
    Until #1673 lands, ensure dependencies do not employ
    namespace packages.
    """
    deps = depends.load_dependencies('cherrypy')
    names = map(package_name, traverse(deps))
    assert not any(name.startswith('jaraco.') for name in names)


def package_name(dep):
    name, sep, ver = dep['resolved'].partition(' ')
    return name


def traverse(pkg):
    yield pkg
    for group in map(traverse, pkg.get('depends', [])):
        for child in group:
            yield child
