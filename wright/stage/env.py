import os
import shlex
import subprocess

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from .base import Check, CheckExec, CheckExecOutput, Stage
from ..util import parse_flags


class CheckWhich(CheckExec):
    cache = False
    order = 10

    def __call__(self, binary, args=()):
        for path in self.env['PATH'].split(':'):
            full = os.path.join(path, binary)
            if os.access(full, os.X_OK):
                return super(CheckWhich, self).__call__((full,) + args)

        return False


class Generate(Check):
    cache = False
    order = 999

    def have(self, *args, **kwargs):
        """Do not export any HAVE_* variables."""
        pass

    def _have(self, name=None):
        """Check if a configure flag is set.

        If called without argument, it returns all HAVE_* items.

        Example:

            {% if have('netinet/ip.h') %}...{% endif %}
        """
        if name is None:
            return (
                (k, v) for k, v  in self.env.items()
                if k.startswith('HAVE_')
            )
        return self.env.get('HAVE_' + self.env_key(name)) == True

    def _lib(self, name, only_if_have=False):
        """Specify a linker library.

        Example:

            LDFLAGS={{ lib("rt") }} {{ lib("pthread", True) }}

        Will unconditionally add `-lrt` and check the environment if the key
        `HAVE_LIBPTHREAD` is set to be true, then add `-lpthread`.
        """
        emit = True
        if only_if_have:
            emit = self.env.get('HAVE_LIB' + self.env_key(name))
        if emit:
            return '-l' + name
        return ''

    def _with(self, option=None):
        """Check if a build option is enabled.

        If called without argument, it returns all WITH_* items.

        Example:

            {% if with('foo') %}...{% endif %}
        """
        if option is None:
            return (
                (k, v) for k, v in self.env.items()
                if k.startswith('WITH_')
            )
        return self.env.get('WITH_' + option.upper()) == True

    def __call__(self, target, source):
        self.output.write('generate: {} from {}\n'.format(target, source))
        env = Environment(loader=FileSystemLoader('.'))
        env.globals['have'] = self._have
        env.globals['lib'] = self._lib
        env.globals['with'] = self._with
        try:
            out = env.get_template(source).render(env=self.env, **self.env)
        except TemplateNotFound as error:
            self.output.write('error: {} not found\n'.format(source))
            return False

        with open(target, 'w') as fp:
            fp.write(out)
        return True


class Flags(CheckExecOutput):
    cache = False
    order = 20

    def __call__(self, name, args):
        for command in args:
            run_args = tuple(shlex.split(command))
            output = super(Flags, self).__call__(run_args)
            if output is None:
                return False

            output = output.strip()
            if output:
                self.env.merge(parse_flags(output))

        return True


class Set(Check):
    cache = False
    order = 10
    quiet = True

    def have(self, *args, **kwargs):
        """Do not export any HAVE_* variables."""
        pass

    def __call__(self, key, value):
        self.env[key] = ' '.join(value)
        return True


class Versions(Check):
    cache = False

    """Generate semantic version numbers from a versions file.

    The file has to have the following contents:

        package=<major>.<minor>.<patch>[-<tag>]

    Optionally, automatic patch version and tagging can be done if executed
    from the root of a git tree.
    """

    def have(self, *args, **kwargs):
        """Do not export any HAVE_* variables."""
        pass

    def __call__(self, source, git=True):
        tag = ''
        patch_git = None
        if git and os.path.isdir('.git'):
            try:
                GIT_VERSION = subprocess.check_output([
                    'git', 'describe', '--long', '--tags',
                ]).strip().split('-')
                tag = 'git'
                patch_git = '-'.join(GIT_VERSION[-2:])

            except subprocess.CalledProcessError:
                tag = 'git'

        with open(source) as fp:
             for line in fp.readlines():
                 line = line.strip()
                 if not line or line.startswith('#'):
                     continue
                 name, version = line.strip().split('=')
                 major, minor, patch = version.strip().split('.')
                 self.env.merge({
                    name.upper() + '_VERSION_MAJOR': major,
                    name.upper() + '_VERSION_MINOR': minor,
                    name.upper() + '_VERSION_PATCH': patch_git or patch,
                    name.upper() + '_VERSION_TAG': tag,
                    name.upper() + '_VERSION': '.'.join([
                        major, minor, patch_git or patch,
                    ]),
                 })

        return True


class Env(Stage):
    def __init__(self, *args, **kwargs):
        super(Env, self).__init__(*args, **kwargs)
        self._check = {
            'binary':   CheckWhich(self),
            'generate': Generate(self),
            'flags':    Flags(self),
            'set':      Set(self),
            'versions': Versions(self),
        }

    def run(self, check):
        if check == 'generate':
            source_fmt = self.config.get('env:generate', 'source')
            for target in self.config.getlist('env:generate', 'target'):
                self.echo('generating ' + target + '...')
                source = source_fmt.format(target=target, env=self.env)
                if self['generate'](target, source):
                    self.echo_result('done', color='green')
                else:
                    self.echo_result('fail', color='red')
                    return False

            return True

        elif check == 'versions':
            sources = self.config.getlist('env:versions', 'source')
            git = self.config.getboolean('env:versions', 'git', False)
            for source in sources:
                self.echo('versions from {}...'.format(source))
                if self['versions'](source, git=git):
                    self.echo_result('done', color='green')
                else:
                    self.echo_result('fail', color='red')
                    return False

            return True
        else:
            return super(Env, self).run(check)
