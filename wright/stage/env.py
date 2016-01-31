import os
import shlex

import jinja2.exceptions
from jinja2 import Environment, FileSystemLoader

from .base import Check, CheckExec, CheckExecOutput, Stage
from ..util import parse_flags


class CheckWhich(CheckExec):
    order = 10

    def __call__(self, binary, args=()):
        for path in self.env['PATH'].split(':'):
            full = os.path.join(path, binary)
            if os.access(full, os.X_OK):
                if super(CheckWhich, self).__call__((full,) + args):
                    return self.have(binary, True)

        return self.have(binary, False)


class Generate(Check):
    order = 999

    def _have(self, name):
        """Check if a configure flag is set.

        Example:

            {% if have('netinet/ip.h') %}...{% endif %}
        """
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

    def _with(self, option):
        """Check if a build option is enabled.

        Example:

            {% if with('foo') %}...{% endif %}
        """
        return self.env.get('WITH_' + option.upper()) == True

    def __call__(self, target, source):
        self.output.write('generate: {} -> {}\n'.format(source, target))
        env = Environment(loader=FileSystemLoader('.'))
        env.globals['have'] = self._have
        env.globals['lib'] = self._lib
        env.globals['with'] = self._with
        try:
            out = env.get_template(source).render(env=self.env)
        except jinja2.exceptions.TemplateNotFound as error:
            self.output.write('error: {} not found\n'.format(source))
            return False

        with open(target, 'w') as fp:
            fp.write(out)
        return True


class Flags(CheckExecOutput):
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


class Env(Stage):
    def __init__(self, *args, **kwargs):
        super(Env, self).__init__(*args, **kwargs)
        self._check = {
            'binary':   CheckWhich(self),
            'generate': Generate(self),
            'flags':    Flags(self),
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
        else:
            return super(Env, self).run(check)
