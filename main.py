'''
Main Server
'''
import asyncio
import websockets
import argparse
import configparser
import os
from pathlib import Path

from libs import server

config = configparser.ConfigParser()
configFile = Path(__file__).parent / ".config"
if os.path.isfile(configFile):
    config.read(configFile)


def get_config_value(section, option, default=None):
    """Helper function to get a value from the config file with a default."""
    return config.get(section, option) if config.has_option(section, option) else default


def parser():
    parse = argparse.ArgumentParser(description='Task Manage Server')
    parse.add_argument("--host", help="Server Host Value")
    parse.add_argument("--port", help="Server Host Value")

    # subparsers = parse.add_subparsers(dest='command')

    # redis_parser = subparsers.add_parser(
    #     'redis', help='Redis server configuration')
    parse.add_argument(
        "--redis-host", help='Redis Host value', dest='redis_host')
    parse.add_argument(
        "--redis-port", help='Redis Port value', dest='redis_port')

    parse.add_argument(
        "--maximum", help='Maximum Run in parallel'
    )
    return parse


def arg_checker(args):
    host = args.host if args.host else get_config_value("server", "host")
    port = args.port if args.port else get_config_value("server", "port")
    redis_host = args.redis_host if args.redis_host else get_config_value(
        "redis", "host")
    redis_port = args.redis_port if args.redis_port else get_config_value(
        "redis", "port"
    )

    maximum = args.maximum if args.maximum else get_config_value(
        'action', 'MAX'
    )
    # Host
    if not host:
        raise Exception("No host value")

    # Port
    if not port:
        raise Exception("No host port value")
    try:
        port = int(port)
    except ValueError:
        raise Exception("Port value must be an integer")

    # Redis Host
    if not redis_host:
        raise Exception("No Redis host")
    # Redis Port
    if not redis_port:
        raise Exception("No Redis port")
    try:
        redis_port = int(redis_port)
    except ValueError:
        raise Exception("Redis port value must be an integer")

    if not maximum:
        raise Exception('No maximum value is set')
    try:
        maximum = int(maximum)
    except ValueError:
        raise Exception("Maximum value should be an integer")

    args.host = host
    args.port = port
    args.redis_host = redis_host
    args.redis_port = redis_port
    args.maximum = maximum


if __name__ == "__main__":
    args = parser().parse_args()
    arg_checker(args)
    service = server.Server(
        args.host, args.port, args.redis_host, args.redis_port, args.maximum
    )

    asyncio.run(service.serve())
