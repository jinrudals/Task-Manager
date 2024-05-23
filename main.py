"""
Main Server
"""
import argparse
import asyncio
import configparser
import os
import logging
from pathlib import Path
from libs import server

# Configure logging
logger = logging.getLogger()

fh = logging.FileHandler("app.log")
fh.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s][%(levelname)s][%(name)s] : %(message)s"
)


fh.setFormatter(formatter)
sh.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(fh)
    logger.addHandler(sh)
config = configparser.ConfigParser()
config_file = Path(__file__).parent / ".config"
if os.path.isfile(config_file):
    config.read(config_file)
    logger.debug("Config file loaded: %s", config_file)


def get_config_value(section, option, default=None):
    """Helper function to get a value from the config file with a default."""
    value = config.get(section, option) if config.has_option(
        section, option) else default
    logger.debug("Config value for [%s] %s: %s", section, option, value)
    return value


def parser():
    '''Argument Parser
    '''
    parse = argparse.ArgumentParser(description='Task Manage Server')
    parse.add_argument("--host", help="Server Host Value")
    parse.add_argument("--port", help="Server Port Value")
    parse.add_argument(
        "--redis-host", help='Redis Host value', dest='redis_host')
    parse.add_argument(
        "--redis-port", help='Redis Port value', dest='redis_port')
    parse.add_argument("--maximum", help='Maximum Run in parallel')
    return parse


def arg_checker(args):
    host = args.host if args.host else get_config_value("server", "host")
    port = args.port if args.port else get_config_value("server", "port")
    redis_host = args.redis_host if args.redis_host else get_config_value(
        "redis", "host")
    redis_port = args.redis_port if args.redis_port else get_config_value(
        "redis", "port")
    maximum = args.maximum if args.maximum else get_config_value(
        'action', 'MAX')

    # Host
    if not host:
        raise Exception("No host value")
    logger.debug("Host value: %s", host)

    # Port
    if not port:
        raise Exception("No host port value")
    try:
        port = int(port)
    except ValueError:
        raise Exception("Port value must be an integer")
    logger.debug("Port value: %d", port)

    # Redis Host
    if not redis_host:
        raise Exception("No Redis host")
    logger.debug("Redis host value: %s", redis_host)

    # Redis Port
    if not redis_port:
        raise Exception("No Redis port")
    try:
        redis_port = int(redis_port)
    except ValueError as exec:
        raise Exception("Redis port value must be an integer") from exec
    logger.debug("Redis port value: %d", redis_port)

    # Maximum
    if not maximum:
        raise Exception('No maximum value is set')
    try:
        maximum = int(maximum)
    except ValueError as exec:
        raise Exception("Maximum value should be an integer") from exec
    logger.debug("Maximum value: %d", maximum)

    args.host = host
    args.port = port
    args.redis_host = redis_host
    args.redis_port = redis_port
    args.maximum = maximum


if __name__ == "__main__":
    args = parser().parse_args()
    logger.debug("Parsed arguments: %s", args)
    arg_checker(args)
    logger.info("Starting server with args: %s", args)
    service = server.Server(args.host, args.port,
                            args.redis_host, args.redis_port, args.maximum)
    asyncio.run(service.serve())
