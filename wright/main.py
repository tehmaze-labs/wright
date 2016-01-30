from __future__ import print_function

import argparse
import os
import sys

from .config import Config
from .log import Logger
from .util import Environment, camel_case, detect_platform, parse_flags, import_module


def main():
    platform = detect_platform()

    parser = argparse.ArgumentParser()
    # Default options
    parser.add_argument('--config', default='wright.conf', metavar='FILE',
        help='wright configuration')
    parser.add_argument('--log', default='wright.log', metavar='FILE',
        help='wright log file (default: wright.log)')
    parser.add_argument('--platform', default=platform,
        help='target platform (default: {})'.format(platform))
    # Cross compiling options
    parser.add_argument('--cross-execute', default='',
        help='cross execute wrapper (default: none)')
    # The rest of the arguments may be environment settings
    parser.add_argument('env', metavar='KEY=VALUE', nargs='*',
        help='additional environment settings')

    args = parser.parse_args()

    env = Environment()
    env.update(os.environ)
    for item in args.env:
        part = item.split('=', 1)
        if len(part) == 1:
            env[item] = ''
        else:
            env[part[0]] = part[1]
    for key in ('ARFLAGS', 'CFLAGS', 'LDFLAGS'):
        env.merge(parse_flags(os.environ.get(key, ''), origin=key))

    if args.cross_execute:
        env['CROSS_EXECUTE'] = args.cross_execute
    if args.platform:
        env['PLATFORM'] = args.platform
        env['PLATFORM_' + args.platform.upper()] = True

    config = Config(env, args.platform)
    if not config.read(args.config):
        print('unable to parse configuration file {}'.format(args.config))
        return 1

    log = Logger(args.log)

    stages = {}
    for stage in config.stages():
        if '.' in stage:
            module = stage
        else:
            module = 'wright.stage.{}'.format(stage)

        stages[stage] = import_module(module)
        log.write('loaded stage {}: {}\n'.format(stage, stages[stage].__file__))
        try:
            stages[stage] = getattr(stages[stage], camel_case(stage))
        except AttributeError:
            raise AttributeError('Stage {} has no class {}'.format(
                stage, camel_case(stage)))
        else:
            # Create instance of the stage (once)
            stages[stage] = stages[stage](config, env, log)

    for name, stage in stages.items():
        log.write('executing stage: {}\n'.format(name))
        for check in stage.checks():
            log.write('executing stage: {}, check: {}\n'.format(name, check))
            if not stage.run(check):
                print('wright failed, check {} for more details'.format(
                    args.log))
                return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
