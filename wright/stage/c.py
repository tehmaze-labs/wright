import shlex

from .base import Check, CheckExec, Stage, TempFile
from ..util import parse_flags


class CheckEnv(Check):
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

        for key in ('CFLAGS', 'LDFLAGS', 'LIBS'):
            try:
                args += tuple(self.env[key])
            except KeyError:
                pass

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
    source = '''
int main() {
#if defined(%s)
    return 0;
#else
    return 42;
#endif
}
'''

    def __call__(self, name, args=()):
        source = self.source % (name,)
        with TempFile('define', '.c', content=source) as temp:
            return self.have(
                name,
                super(CheckDefine, self).__call__(temp.filename, args, run=True),
            )


class CheckFeature(CheckCompile):
    def __call__(self, feature, args):
        source = args[0]
        args = args[1:]
        return self.have(
            feature,
            super(CheckFeature, self).__call__(source, args, run=True),
        )


class CheckHeader(CheckCompile):
    source = '''
#include <%s>
int main() { return 0; }
'''

    def __call__(self, name, args=()):
        source = self.source % (name,)
        with TempFile('header', '.c', content=source) as temp:
            return self.have(
                name,
                super(CheckHeader, self).__call__(temp.filename, args),
            )


class CheckLibrary(CheckCompile):
    source = '''
int main() {
    return 0;
}
'''

    def __call__(self, name, headers=()):
        source = ''
        for header in headers:
            source += '#include <%s>\n' % (header,)
        source += self.source
        with TempFile('library', '.c', content=source) as temp:
            args = ('-l' + name,)
            return self.have(
                'lib' + name,
                super(CheckLibrary, self).__call__(temp.filename, args),
            )


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
        }
