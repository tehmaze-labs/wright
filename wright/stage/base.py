import os
import re
import subprocess
import sys
import tempfile

from ..util import normal_case

RE_ENV_UNSAFE = re.compile(r'[^\w_]')


try:
    foo = WindowsError
except NameError:
    class WindowsError(IOError):
        pass


class Check(object):
    order = 100
    quiet = False

    def __init__(self, stage):
        self.stage = stage
        self.env = self.stage.env
        self.output = self.stage.output

    def env_key(self, item):
        return RE_ENV_UNSAFE.sub('_', item).strip('_').upper()


    def have(self, what, success):
        success = bool(success)
        self.env['HAVE_' + self.env_key(what)] = success
        return success

    @property
    def name(self):
        if self.__class__.__name__.startswith('Check'):
            return normal_case(self.__class__.__name__[5:])
        return normal_case(self.__class__.__name__)

    def __call__(self, *args):
        return False


class CheckExec(Check):
    def __call__(self, args):
        self.output.write('exec: {}\n'.format(' '.join(args)))
        self.output.flush()
        try:
            code = subprocess.call(
                args,
                stdout=self.output,
                stderr=self.output)
        except WindowsError:
            code = errno.errorcode

        self.output.write('return code: {}\n'.format(code))
        self.output.flush()
        return code == 0


class CheckExecOutput(Check):
    def __call__(self, args):
        self.output.write('exec: {}\n'.format(' '.join(args)))
        self.output.flush()
        try:
            pipe = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=self.output)
            text = pipe.communicate()[0]
            self.output.write('result:\n{}\n'.format(text.strip()))
            self.output.flush()
            if pipe.returncode == 0:
                return text
        except WindowsError:
            return None


class Stage(object):
    color = {
        'normal': '\x1b[0m',
        'red':    '\x1b[1;31m',
        'green':  '\x1b[1;32m',
        'yellow': '\x1b[1;33m',
        'blue':   '\x1b[1;34m',
    }

    def __init__(self, config, env={}, output=sys.stderr):
        self.config = config
        self.env = env
        self.x_pos = 0
        self.output = output
        # Registry of check commands
        self._check = {}

    def __getitem__(self, check):
        return self._check[check]

    @property
    def name(self):
        return normal_case(self.__class__.__name__)

    def checks(self):
        checks = self._check.items()
        checks.sort(key=lambda item: item[1].order)
        for name, _ in checks:
            if self.config.has_check(self.name, name):
                yield name

    def checking(self, what):
        self.echo('checking {}...'.format(what))

    def echo(self, what, color='normal'):
        what = str(what)
        self.x_pos += len(what)
        sys.stdout.write(''.join([
            self.color[color],
            what,
            self.color['normal'],
        ]))
        sys.stdout.flush()

    def echo_result(self, result, color='normal'):
        pad = ' ' * max(0, 64 - self.x_pos)
        self.echo(pad + result + '\n', color=color)
        self.x_pos = 0

    def run(self, check):
        self.output.write('stage {}.{}:\n'.format(self.name, check))
        for name, args in self.config.required(self.name, check):
            if not self._run_check(check, name, args):
                return False

        for name, args in self.config.optional(self.name, check):
            self._run_check(check, name, args, True)

        return True

    def _run_check(self, check, name, args, optional=False):
        self.output.write('stage {}.{}: run name={!r}, args={!r}\n'.format(
            self.name, check, name, args))
        try:
            test = self[check]
        except KeyError:
            self.echo_result('fail', color='red')
            self.echo('stage "{}" has no check "{}"\n'.format(self.name, check))
            return False

        if not test.quiet:
            self.checking(' '.join([check, name]))
        if test(name, args):
            if not test.quiet:
                self.echo_result('yes', color='green')
            return True
        else:
            if not test.quiet:
                self.echo_result('no', color='yellow' if optional else 'red')
            return False


class TempFile:
    def __init__(self, prefix='', suffix='tmp', content=None):
        self.prefix = prefix
        self.suffix = suffix
        self.content = content
        self.filename = None

    def __enter__(self):
        fd, self.filename = tempfile.mkstemp(
            suffix=self.suffix,
            prefix=self.prefix)
        if self.content is not None:
            os.write(fd, self.content)
        return self

    def __exit__(self, typ, value, traceback):
        if self.filename is not None:
            try:
                os.unlink(self.filename)
            except (IOError, OSError):
                pass
            self.filename = None
