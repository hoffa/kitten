#!/usr/bin/env python

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import functools
import logging
import os
import re
import signal
import sys
import threading

import boto3
import fabric
from six.moves import range, queue

__version__ = "0.3.1"

CHUNK_SIZE = 50
DEFAULT = {"threads": 10, "timeout": 10}
HELP = {
    "command": "shell command to execute",
    "hosts": "list of IP addresses",
    "i": "private key path",
    "kind": "AWS resource type",
    "local": "path to local file",
    "public": "print public IP addresses if possible",
    "region": "AWS region name",
    "remote": "path to remote file",
    "threads": "number of concurrent connections (default: {})".format(
        DEFAULT["threads"]
    ),
    "timeout": "connection timeout in seconds (default: {})".format(DEFAULT["timeout"]),
    "user": "remote connection user",
    "values": "list of instance IDs or resource names",
    "verbose": "show more output",
}

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))

tasks = queue.Queue()
stop = threading.Event()


def ansi(x):
    return "\033[{}m".format(x)


def colored(s, code=0, bold=False):
    has_attr = code > 0 or bold
    if has_attr and sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        bold_attr = ansi(1) if bold else ""
        return ansi(code) + bold_attr + s + ansi(0)
    return s


def red(s):
    return colored(s, code=31)


def green(s):
    return colored(s, code=32)


def yellow(s):
    return colored(s, code=33)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


class Connection(object):
    """
    Encapsulates an SSH connection.
    """

    def __init__(self, host, user, timeout, key_filename, color):
        self.host = host
        self.color = color
        self.conn = fabric.Connection(
            host,
            user=user,
            connect_timeout=timeout,
            connect_kwargs={
                "key_filename": key_filename,
                "auth_timeout": timeout,
                "banner_timeout": timeout,
            },
        )

    def print(self, s, color=colored):
        for line in s.splitlines():
            log.info(self.color(self.host) + "\t" + color(line))

    def run(self, command):
        self.print("{}\t{}".format(yellow("run"), command))
        try:
            with self.conn as c:
                result = c.run(command, pty=True, hide=True, warn=True, in_stream=False)
        except Exception as e:
            self.print(str(e), color=red)
        else:
            color = colored if result.ok else red
            self.print(result.stdout, color=color)

    def put(self, local, remote):
        self.print("{}\t{}\t{}".format(yellow("put"), local, remote))
        try:
            with self.conn as c:
                c.put(local, remote=remote)
        except Exception as e:
            self.print(str(e), color=red)
        else:
            self.print("ok", color=green)

    def get(self, remote):
        local = os.path.join(self.host, os.path.basename(remote))
        self.print("{}\t{}\t{}".format(yellow("get"), remote, local))
        try:
            os.mkdir(self.host)
        except OSError:
            pass
        try:
            with self.conn as c:
                c.get(remote, local=local)
        except Exception as e:
            self.print(str(e), color=red)
        else:
            self.print("ok", color=green)


def find_instance_ids(l):
    for s in l:
        for match in re.findall(r"[\da-f]{17}|[\da-f]{8}", s):
            yield "i-" + match


def describe_instances(client, filters):
    reservations = client.describe_instances(Filters=filters)
    for reservation in reservations["Reservations"]:
        for instance in reservation["Instances"]:
            yield instance


def instance_ids_to_ip_addrs(client, instance_ids):
    # Send request in batches to avoid FilterLimitExceeded. Use Filters
    # instead of InstanceIds to avoid exception on non-existent instance ID
    # (e.g. during scale-out or when hastily pasting a bunch of text).
    for chunk in chunks(list(instance_ids), CHUNK_SIZE):
        filters = [{"Name": "instance-id", "Values": chunk}]
        for instance in describe_instances(client, filters):
            yield {
                "public": instance.get("PublicIpAddress"),
                "private": instance.get("PrivateIpAddress"),
            }


def opsworks_layer_ids_to_ip_addrs(client, layer_ids):
    for layer_id in layer_ids:
        instances = client.describe_instances(LayerId=layer_id)
        for instance in instances["Instances"]:
            yield {
                "public": instance.get("PublicIp"),
                "private": instance.get("PrivateIp"),
            }


def asgs_to_instance_ids(client, asg_names):
    asgs = client.describe_auto_scaling_groups(AutoScalingGroupNames=asg_names)
    for asg in asgs["AutoScalingGroups"]:
        for instance in asg["Instances"]:
            yield instance["InstanceId"]


def elbs_to_instance_ids(client, elb_names):
    elbs = client.describe_load_balancers(LoadBalancerNames=elb_names)
    for elb in elbs["LoadBalancerDescriptions"]:
        for instance in elb["Instances"]:
            yield instance["InstanceId"]


def print_ip_addrs(ip_addrs, public):
    for ip_addr in ip_addrs:
        public_ip = ip_addr["public"]
        private_ip = ip_addr["private"]
        if public and public_ip:
            log.info(public_ip)
        elif private_ip:
            log.info(private_ip)


def get_ip_addrs(values, kind, region_name):
    if kind == "opsworks":
        opsworks = boto3.client("opsworks", region_name=region_name)
        return opsworks_layer_ids_to_ip_addrs(opsworks, values)
    elif kind == "id":
        instance_ids = find_instance_ids(values)
    elif kind == "asg":
        autoscaling = boto3.client("autoscaling", region_name=region_name)
        instance_ids = asgs_to_instance_ids(autoscaling, values)
    elif kind == "elb":
        elb = boto3.client("elb", region_name=region_name)
        instance_ids = elbs_to_instance_ids(elb, values)
    ec2 = boto3.client("ec2", region_name=region_name)
    return instance_ids_to_ip_addrs(ec2, instance_ids)


def get_colors():
    for bold in (False, True):
        for code in range(31, 37):
            yield functools.partial(colored, code=code, bold=bold)


def get_conns(args):
    colors = list(get_colors())
    for i, host in enumerate(args.hosts):
        yield Connection(host, args.user, args.timeout, args.i, colors[i % len(colors)])


def get_tasks(args):
    conns = get_conns(args)
    if args.tool == "run":
        return [functools.partial(conn.run, args.command) for conn in conns]
    elif args.tool == "get":
        return [functools.partial(conn.get, args.remote) for conn in conns]
    elif args.tool == "put":
        return [functools.partial(conn.put, args.local, args.remote) for conn in conns]


def worker():
    while not stop.is_set():
        try:
            task = tasks.get_nowait()
            task()
            tasks.task_done()
        except queue.Empty:
            break


def run_workers(num_workers):
    threads = []
    for _ in range(num_workers):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    for thread in threads:
        while thread.is_alive():
            thread.join(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Tiny multi-server automation tool.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", action="store_true", help=HELP["verbose"])
    subparsers = parser.add_subparsers(dest="tool")

    aws_parser = subparsers.add_parser("ip")
    aws_parser.add_argument("--region", help=HELP["region"])
    aws_parser.add_argument("--public", action="store_true", help=HELP["public"])
    aws_parser.add_argument(
        "kind", choices=("id", "asg", "elb", "opsworks"), help=HELP["kind"]
    )
    aws_parser.add_argument("values", nargs="+", help=HELP["values"])

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("-i", help=HELP["i"])
    run_parser.add_argument(
        "--timeout", type=float, default=DEFAULT["timeout"], help=HELP["timeout"]
    )
    run_parser.add_argument(
        "--threads", type=int, default=DEFAULT["threads"], help=HELP["threads"]
    )
    run_parser.add_argument("command", help=HELP["command"])
    run_parser.add_argument("user", help=HELP["user"])
    run_parser.add_argument("hosts", nargs="+", help=HELP["hosts"])

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("-i", help=HELP["i"])
    get_parser.add_argument(
        "--timeout", type=float, default=DEFAULT["timeout"], help=HELP["timeout"]
    )
    get_parser.add_argument(
        "--threads", type=int, default=DEFAULT["threads"], help=HELP["threads"]
    )
    get_parser.add_argument("remote", help=HELP["remote"])
    get_parser.add_argument("user", help=HELP["user"])
    get_parser.add_argument("hosts", nargs="+", help=HELP["hosts"])

    put_parser = subparsers.add_parser("put")
    put_parser.add_argument("-i", help=HELP["i"])
    put_parser.add_argument(
        "--timeout", type=float, default=DEFAULT["timeout"], help=HELP["timeout"]
    )
    put_parser.add_argument(
        "--threads", type=int, default=DEFAULT["threads"], help=HELP["threads"]
    )
    put_parser.add_argument("local", help=HELP["local"])
    put_parser.add_argument("remote", help=HELP["remote"])
    put_parser.add_argument("user", help=HELP["user"])
    put_parser.add_argument("hosts", nargs="+", help=HELP["hosts"])

    args = parser.parse_args()
    if not args.tool:
        parser.print_help()
        sys.exit(2)

    return args


def main():
    # Avoid throwing exception on SIGPIPE.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if args.tool == "ip":
        print_ip_addrs(get_ip_addrs(args.values, args.kind, args.region), args.public)
    else:
        for task in get_tasks(args):
            tasks.put_nowait(task)
        try:
            num_workers = min(args.threads, len(args.hosts))
            run_workers(num_workers)
        except KeyboardInterrupt:
            log.info(red("terminating"))
            stop.set()


if __name__ == "__main__":
    main()
