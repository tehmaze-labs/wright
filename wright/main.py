from __future__ import print_function

import argparse
import os
import sys

from .config import Config
from .cache import Cache
from .log import Logger
from .util import Environment, camel_case, detect_platform, parse_flags, import_module


def main():
    platform = detect_platform()

    parser = argparse.ArgumentParser(
        epilog='to see the full list of build options, run with --help-options',
        add_help=False,
    )
    # Default options
    group = parser.add_argument_group('wright options')
    group.add_argument('--help-options', action='store_true',
        help='show build options')
    group.add_argument('--cache', default='wright.cache', metavar='<file>',
        help='write configuration cache (default: wright.cache)')
    group.add_argument('--config', default='wright.ini', metavar='<file>',
        help='wright configuration (default: wright.ini)')
    group.add_argument('--log', default='wright.log', metavar='<file>',
        help='wright log file (default: wright.log)')
    group.add_argument('--platform', default=platform, metavar='<name>',
        help='target platform (default: {})'.format(platform))
    # Cross compiling options
    group = parser.add_argument_group('compiler options')
    group.add_argument('--cross-compile', default='', metavar='<prefix>',
        help='cross compile prefix (default: none)')
    group.add_argument('--cross-execute', default='', metavar='<exec>',
        help='cross execute wrapper (default: none)')
    # The rest of the arguments may be environment settings
    parser.add_argument('env', metavar='key=value', nargs='*',
        help='additional environment settings')

    # Parse the arguments that are known to us, so we can extend them from our
    # configuration file.
    args, remaining_args = parser.parse_known_args()

    env = Environment(args.platform)
    env.update(os.environ)
    for item in args.env:
        part = item.split('=', 1)
        if len(part) == 1:
            env[item] = ''
        else:
            env[part[0]] = part[1]
    for key in ('ARFLAGS', 'CFLAGS', 'LDFLAGS'):
        env.merge(parse_flags(os.environ.get(key, ''), origin=key))

    if args.cross_compile:
        env['CROSS_COMPILE'] = args.cross_compile
    if args.cross_execute:
        env['CROSS_EXECUTE'] = args.cross_execute
    if args.platform:
        env['PLATFORM'] = args.platform
        env['PLATFORM_' + args.platform.upper()] = True

    config = Config(env, args.platform)
    if not config.read(args.config):
        print('unable to parse configuration file {}'.format(args.config))
        return 1

    # Check our configuration file mtime
    config_time = os.stat(args.config).st_mtime

    # Now is a good time to parse the rest of the arguments
    options_parser = argparse.ArgumentParser(parents=[parser])
    options_parser.set_defaults(**args.__dict__)
    config.add_arguments(options_parser)
    args = options_parser.parse_args(remaining_args)

    if args.help_options:
        options_parser.print_help()
        return 0

    # Feed back the build options to our environment
    for key, value in args.__dict__.items():
        env[key.upper()] = value

    log = Logger(args.log)
    if config.getboolean('cache', 'enabled', True) and args.cache:
        marshaler = config.get('cache', 'marshaler', 'json')
        log.write('cache: {} from {}\n'.format(marshaler, args.cache))
        cache = Cache(args.platform, marshaler=marshaler)
        cache.open(args.cache, not_before=config_time)
    else:
        cache = dict()

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
            stages[stage] = stages[stage](config, cache, env, log)

    for name, stage in stages.items():
        log.write('executing stage: {}\n'.format(name))
        for check in stage.checks():
            log.write('executing stage: {}, check: {}\n'.format(name, check))
            if not stage.run(check):
                print('wright failed, check {} for more details'.format(
                    args.log))
                return 1

    for key in sorted(env):
        if key.startswith('HAVE_') or key.startswith('WITH_'):
            log.write('env: {}={}\n'.format(key, env[key]))

    return 0


if __name__ == '__main__':
    sys.exit(main())
