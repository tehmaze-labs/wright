import collections
import re
import shlex
import sys


if sys.hexversion < 0x03000000:
    STR_TYPES = (str, unicode)
else:
    STR_TYPES = str


class OrderedSet(collections.MutableSet):
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


class Environment(dict):
    defaults = {
        'linux': {
            'BINEXT': '',
            'ARLIBPRE': 'lib',
            'ARLIBEXT': '.a',
            'SHLIBPRE': 'lib',
            'SHLIBEXT': '.so',
        },
        'osx': {
            'BINEXT': '',
            'ARLIBPRE': 'lib',
            'ARLIBEXT': '.a',
            'SHLIBPRE': 'lib',
            'SHLIBEXT': '.dylib',
        },
        'win32': {
            'BINEXT':   '.exe',
            'ARLIBPRE': 'lib',
            'ARLIBEXT': '.a',
            'SHLIBPRE': '',
            'SHLIBEXT': '.dll',
        },
    }

    def __init__(self, platform):
        self.update(self.defaults.get(platform, {}))

    def merge(self, other):
        """Merge other (dict or OrderedSet) into this environment.

        Only works for basic types: str, list, tuple, dict and OrderedSet.
        """
        for key, value in other.items():
            if not key in self:
                self[key] = value
            elif isinstance(value, (list, tuple)):
                self[key] += value
            elif isinstance(value, OrderedSet):
                if isinstance(self[key], str):
                    self[key] = OrderedSet([self[key]])
                elif not isinstance(self[key], OrderedSet):
                    self[key] = OrderedSet(self[key])
                self[key] |= value
            else:
                self[key] = value
        return self


def camel_case(name):
    """Convert words into CamelCase."""
    return ''.join(name.capitalize().split())


def normal_case(name):
    """Converts "CamelCaseHere" to "camel case here"."""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s1).lower()


def detect_platform():
    platform = sys.platform
    if platform in ('linux', 'linux2'):
        return 'linux'

    elif platform in ('darwin',):
        return 'osx'

    elif platform in ('win32',):
        return 'windows'

    else:
        return platform


def import_module(name):
    module = __import__(name)
    for part in name.split('.')[1:]:
        module = getattr(module, part)
    return module


def parse_bool(value, default=True, strict=True):
    if value.lower() in ('true', 'yes', 'on', '1'):
        return True
    elif value.lower() in ('false', 'no', 'off', '0'):
        return False
    elif strict:
        raise ValueError(value)
    else:
        return default


def parse_flags(*flags, **kwargs):
    """Parse compile flags."""

    parsed = {
        'ASFLAGS':       OrderedSet(),
        'CFLAGS':        OrderedSet(),
        'DEFINES':       OrderedSet(),
        'INCLUDES':      OrderedSet(),
        'FRAMEWORKS':    OrderedSet(),
        'FRAMEWORKPATH': OrderedSet(),
        'LDFLAGS':       OrderedSet(),
        'LIBS':          OrderedSet(),
        'LIBPATH':       OrderedSet(),
    }

    def _parse(arg):
        if not arg:
            return

        if not isinstance(arg, STR_TYPES):
            for item in arg:
                _parse(arg)
            return

        def add_define(name):
            part = name.split('=')
            if len(part) == 1:
                parsed['DEFINES'].add(name)
            else:
                parsed['DEFINES'].add([part[0], '='.join(part[1:])])

        part = shlex.split(arg)
        curr = None   # For multiword arguments
        for item in part:
            if curr is not None:
                if curr == 'DEFINES':
                    add_define(item)
                elif curr == '-include':
                    parsed['CFLAGS'].add(('-include', item))
                elif curr == '-isysroot':
                    parsed['CFLAGS'].add(('-isysroot', item))
                    parsed['LDFLAGS'].add(('-isysroot', item))
                elif curr == '-arch':
                    parsed['CFLAGS'].add(('-arch', item))
                    parsed['LDFLAGS'].add(('-arch', item))
                else:
                    parsed[curr].add(item)
                curr = None

            elif not item[0] in '-+':
                parsed['LIBS'].add(item)

            elif item == '-dylib_file':
                parsed['LDFLAGS'].add(item)
                curr = 'LDFLAGS'

            elif item[:2] == '-L':
                if item[2:]:
                    parsed['LIBPATH'].add(item[2:])
                else:
                    curr = 'LIBPATH'

            elif item[:2] == '-l':
                if item[2:]:
                    parsed['LIBS'].add(item[2:])
                else:
                    curr = 'LIBS'

            elif item[:2] == '-I':
                if item[2:]:
                    parsed['INCLUDES'].add(item[2:])
                else:
                    curr = 'INCLUDES'

            elif item[:4] == '-Wa,':
                parsed['ASFLAGS'].add(arg[4:])
                parsed['CFLAGS'].add(item)

            elif item[:4] == '-Wp,':
                parsed['CFLAGS'].add(item)

            elif item[:2] == '-D':
                if item[2:]:
                    parsed['DEFINES'].add(item[2:])
                else:
                    curr = 'DEFINES'

            elif item == '-framework':
                curr = 'FRAMEWORKS'

            elif item[:14] == '-frameworkdir=':
                parsed['FRAMEWORKPATH'].add(item[14:])

            elif item[:2] == '-F':
                if item[2:]:
                    parsed['FRAMEWORKPATH'].add(item[2:])
                else:
                    curr = 'FRAMEWORKPATH'

            elif item in ('-mno-cygwin', '-pthread', '-openmp', '-fopenmp'):
                parsed['CFLAGS'].add(item)
                parsed['LDFLAGS'].add(item)

            elif item == '-mwindows':
                parsed['LDFLAGS'].add(item)

            elif item[:5] == '-std=':
                parsed['CFLAGS'].add(item)

            elif item[0] == '+':
                parsed['CFLAGS'].add(item)
                parsed['LDFLAGS'].add(item)

            elif item in ('-include', '-isysroot', '-arch'):
                curr = item

            else:
                parsed[kwargs.get('origin', 'CFLAGS')].add(item)

    for arg in flags:
        _parse(arg)

    return parsed


def yield_from(generate):
    for item in generate:
        yield item
