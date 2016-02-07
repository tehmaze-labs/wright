import shlex

from .base import Check, CheckExec, Stage, TempFile
from ..util import parse_flags


class CheckEnv(Check):
    cache = False
    order = 50
    quiet = True

    def __call__(self, *args):
        for arg in args:
            if not arg:
                continue
            arg = arg.format(**self.env)
            self.env.merge(parse_flags(arg))
        return True


class CheckCompile(CheckExec):
    def __call__(self, source, args=(), run=False):
        cross_compile = self.env.get('CROSS_COMPILE', '')
        cross_execute = shlex.split(self.env.get('CROSS_EXECUTE', ''))
        cc = self.env.get('CC', 'gcc')
        compiler = cross_compile + cc

        for path in self.env.get('LIBPATH', []):
            args += ('-L' + path,)

        for inc in self.env.get('INCLUDES', []):
            args += ('-I' + inc,)

        with open(source, 'r') as fp:
            self.output.write('script: %s\n%s\n' % (source, fp.read()))

        with TempFile('compile') as temp:
            if super(CheckCompile, self).__call__((
                    compiler, source, '-o', temp.filename,
                ) + args):
                if not run:
                    return True

                run_args = (temp.filename,)
                if cross_execute:
                    run_args = tuple(cross_execute) + run_args
                return super(CheckCompile, self).__call__(run_args)


class CheckDefine(CheckCompile):
    order = 100
    source = '''
int main() {
#if defined(%s)
    return 0;
#else
    return 42;
#endif
}
'''

    def __call__(self, name, headers=()):
        source = self.source % (name,)
        for header in headers:
            source = '#include <{}>\n'.format(header)
        with TempFile('define', '.c', content=source) as temp:
            return super(CheckDefine, self).__call__(temp.filename, run=True)


class CheckFeature(CheckCompile):
    def __call__(self, feature, args):
        source = args[0]
        args = args[1:]
        return super(CheckFeature, self).__call__(source, args, run=True)


class CheckHeader(CheckCompile):
    order = 200
    source = '''
#include <%s>
int main() { return 0; }
'''

    def __call__(self, name, args=()):
        source = self.source % (name,)
        with TempFile('header', '.c', content=source) as temp:
            return super(CheckHeader, self).__call__(temp.filename, args)


class CheckLibrary(CheckCompile):
    order = 500
    source = '''
int main() {
    return 0;
}
'''

    def have(self, what, success):
        return super(CheckLibrary, self).have('lib' + what, success)

    def __call__(self, name, headers=()):
        source = ''
        for header in headers:
            source += '#include <%s>\n' % (header,)
        source += self.source
        with TempFile('library', '.c', content=source) as temp:
            args = ('-l' + name,)
            return super(CheckLibrary, self).__call__(temp.filename, args)


class CheckType(CheckCompile):
    """Check for type.

    Example::

        [c:type]
        required = uint8_t: inttypes.h
    """

    order = 300
    source = '''
int main() {
    %(ctype)s check_type_test;
    return 0;
}
'''

    def __call__(self, ctype, headers=()):
        source = ''
        for header in headers:
            source += '#include <%s>\n' % (header,)
        source += self.source % {'ctype': ctype}
        with TempFile('type', '.c', content=source) as temp:
            args = ('-Wno-unused-variable',)
            return super(CheckType, self).__call__(temp.filename, args)


class CheckMember(CheckCompile):
    """Check for type members, such as structs.

    Example::

        [c:member]
        required = struct termios.c_ispeed: linux/termios.h
    """

    order = 350
    source = '''
int main() {
    %(ctype)s check_type_test;
    (void)check_type_test.%(member)s;
    return 0;
}
'''

    def __call__(self, ctype_with_member, headers=()):
        attr = {}
        attr['ctype'], attr['member'] = ctype_with_member.split('.', 1)
        source = ''
        for header in headers:
            source += '#include <%s>\n' % (header,)
        source += self.source % attr
        with TempFile('type', '.c', content=source) as temp:
            args = ('-Wno-unused-variable',)
            return super(CheckMember, self).__call__(temp.filename, args)


class C(Stage):
    def __init__(self, *args, **kwargs):
        super(C, self).__init__(*args, **kwargs)
        self._check = {
            'env':     CheckEnv(self),
            'compile': CheckCompile(self),
            'define':  CheckDefine(self),
            'feature': CheckFeature(self),
            'header':  CheckHeader(self),
            'library': CheckLibrary(self),
            'type':    CheckType(self),
            'member':  CheckMember(self),
        }
