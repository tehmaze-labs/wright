try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

from .util import yield_from


class Config(RawConfigParser):
    def __init__(self, env, platform):
        RawConfigParser.__init__(self)
        self.env = env
        self.platform = platform

    def getlist(self, section, option):
        return [
            line.strip()
            for line in self.get(section, option).strip().splitlines()
        ]

    def has_check(self, stage, check):
        section = ':'.join([stage, check])
        return self.has_section(section)

    def _suboptions(self, stage, check, option):
        section = ':'.join([stage, check])
        if not self.has_option(section, option):
            return

        for line in self.getlist(section, option):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = [part.strip() for part in line.split(':', 1)]
            if len(parts) == 1:
                if parts[0].startswith('<'):
                    for nested in self._suboptions(stage, check, parts[0][1:].strip()):
                        yield nested

                else:
                    yield (parts[0], ())
            else:
                yield (
                    parts[0],
                    tuple([part.strip() for part in parts[1].split(',')])
                )

    def _conditional_checks(self, stage, check, kind):
        yield kind
        yield kind + '_' + self.platform
        section = ':'.join([stage, check])
        for option in self.options(section):
            if option.startswith(kind + '_if_'):
                """
                Condition here is another environment variable, e.g. `HAVE_FOO`,
                so one can write:

                    optional_if_HAVE_FOO = item, item, ...
                """
                condition = option[len(kind) + 4:].upper()
                if self.env.get(condition):
                    yield option

    def optional(self, stage, check):
        for key in self._conditional_checks(stage, check, 'optional'):
            for item in self._suboptions(stage, check, key):
                yield item


    def required(self, stage, check):
        for key in self._conditional_checks(stage, check, 'required'):
            for item in self._suboptions(stage, check, key):
                yield item

    def stages(self):
        for stage in self.get('configure', 'stages').split(','):
            yield stage.strip()

    def stage_checks(self, stage):
        for section in self.sections():
            if section.startswith(stage + ':'):
                yield section[len(stage) + 1:]
