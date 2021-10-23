#!/usr/bin/env python3

import argparse
import functools
import logging
import os
import queue
import re
import signal
import sys
import threading
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
)

import boto3  # type: ignore
import fabric  # type: ignore

T = TypeVar("T")
ColorFunc = Callable[[str], str]
TaskFunc = Callable[[], None]
Ip = Dict[str, Optional[str]]
Filters = List[Dict[str, Union[str, List[str]]]]

__version__ = "0.6.2"

CHUNK_SIZE = 50
DEFAULT = {"threads": 10, "timeout": 10}
HELP = {
    "command": "shell command to execute",
    "hosts": "list of IP addresses",
    "i": "private key path",
    "kind": "AWS resource type (id: instance ID, asg: Auto Scaling Group name, elb: Elastic Load Balancer name)",
    "local": "path to local file",
    "public": "prefer public IP addresses",
    "region": "AWS region name",
    "remote": "path to remote file",
    "threads": "number of concurrent connections",
    "timeout": "connection timeout in seconds",
    "user": "remote server user",
    "values": "list of resource identifiers",
    "verbose": "show more output",
}

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))

tasks: "queue.Queue[TaskFunc]" = queue.Queue()
stop = threading.Event()
num_success = 0
lock = threading.Lock()


def inc_success() -> None:
    global num_success
    with lock:
        num_success += 1


def ansi(x: int) -> str:
    return "\033[{}m".format(x)


def colored(s: str, code: int = 0, bold: bool = False) -> str:
    has_attr = code > 0 or bold
    if has_attr and sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        bold_attr = ansi(1) if bold else ""
        return ansi(code) + bold_attr + s + ansi(0)
    return s


def red(s: str) -> str:
    return colored(s, code=31)


def green(s: str) -> str:
    return colored(s, code=32)


def yellow(s: str) -> str:
    return colored(s, code=33)


def chunks(L: List[T], n: int) -> Iterator[List[T]]:
    for i in range(0, len(L), n):
        yield L[i : i + n]


class Connection(object):
    def __init__(
        self, host: str, user: str, timeout: int, key_filename: str, color: ColorFunc
    ) -> None:
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

    def print(self, s: str, color: ColorFunc = colored) -> None:
        for line in s.splitlines():
            log.info(self.color(self.host) + "\t" + color(line))

    def run(self, command: str) -> None:
        self.print("{}\t{}".format(yellow("run"), command))
        try:
            with self.conn as c:
                result = c.run(command, pty=True, hide=True, warn=True, in_stream=False)
        except Exception as e:
            self.print(str(e), color=red)
        else:
            if result.ok:
                self.print(result.stdout)
                inc_success()
            else:
                self.print(result.stdout, color=red)

    def put(self, local: str, remote: str) -> None:
        self.print("{}\t{}\t{}".format(yellow("put"), local, remote))
        try:
            with self.conn as c:
                c.put(local, remote=remote)
        except Exception as e:
            self.print(str(e), color=red)
        else:
            self.print("ok", color=green)
            inc_success()

    def get(self, remote: str) -> None:
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
            inc_success()


def find_instance_ids(L: List[str]) -> Iterator[str]:
    for s in L:
        for match in re.findall(r"[\da-f]{17}|[\da-f]{8}", s):
            yield "i-" + match


def describe_instances(client: Any, filters: Filters) -> Iterator[Dict[str, str]]:
    reservations = client.describe_instances(Filters=filters)
    for reservation in reservations["Reservations"]:
        for instance in reservation["Instances"]:
            yield instance


def instance_ids_to_ip_addrs(client: Any, instance_ids: Iterable[str]) -> Iterator[Ip]:
    # Send request in batches to avoid FilterLimitExceeded. Use Filters
    # instead of InstanceIds to avoid exception on non-existent instance ID
    # (e.g. during scale-out or when hastily pasting a bunch of text).
    for chunk in chunks(list(instance_ids), CHUNK_SIZE):
        filters: Filters = [{"Name": "instance-id", "Values": chunk}]
        for instance in describe_instances(client, filters):
            yield {
                "public": instance.get("PublicIpAddress"),
                "private": instance.get("PrivateIpAddress"),
            }


def asgs_to_instance_ids(client: Any, asg_names: List[str]) -> Iterator[str]:
    asgs = client.describe_auto_scaling_groups(AutoScalingGroupNames=asg_names)
    for asg in asgs["AutoScalingGroups"]:
        for instance in asg["Instances"]:
            yield instance["InstanceId"]


def elbs_to_instance_ids(client: Any, elb_names: List[str]) -> Iterator[str]:
    elbs = client.describe_load_balancers(LoadBalancerNames=elb_names)
    for elb in elbs["LoadBalancerDescriptions"]:
        for instance in elb["Instances"]:
            yield instance["InstanceId"]


def print_ip_addrs(ip_addrs: Iterable[Ip], public: bool) -> None:
    for ip_addr in ip_addrs:
        public_ip = ip_addr["public"]
        private_ip = ip_addr["private"]
        if public and public_ip:
            log.info(public_ip)
        elif private_ip:
            log.info(private_ip)


def get_ip_addrs(values: List[str], kind: str, region_name: str) -> Iterator[Ip]:
    if kind == "id":
        instance_ids = find_instance_ids(values)
    elif kind == "asg":
        autoscaling = boto3.client("autoscaling", region_name=region_name)
        instance_ids = asgs_to_instance_ids(autoscaling, values)
    elif kind == "elb":
        elb = boto3.client("elb", region_name=region_name)
        instance_ids = elbs_to_instance_ids(elb, values)
    ec2 = boto3.client("ec2", region_name=region_name)
    return instance_ids_to_ip_addrs(ec2, instance_ids)


def get_colors() -> Iterator[ColorFunc]:
    for bold in (False, True):
        for code in range(31, 37):
            yield functools.partial(colored, code=code, bold=bold)


def get_conns(args: argparse.Namespace) -> Iterator[Connection]:
    colors = list(get_colors())
    for i, host in enumerate(args.hosts):
        if host:
            yield Connection(
                host, args.user, args.timeout, args.i, colors[i % len(colors)]
            )


def get_tasks(args: argparse.Namespace) -> List[TaskFunc]:
    conns = get_conns(args)
    if args.tool == "run":
        return [functools.partial(conn.run, args.command) for conn in conns]
    elif args.tool == "get":
        return [functools.partial(conn.get, args.remote) for conn in conns]
    elif args.tool == "put":
        return [functools.partial(conn.put, args.local, args.remote) for conn in conns]
    return []


def worker() -> None:
    while not stop.is_set():
        try:
            task = tasks.get_nowait()
            task()
            tasks.task_done()
        except queue.Empty:
            break


def run_workers(num_workers: int) -> None:
    threads = []
    for _ in range(num_workers):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    for thread in threads:
        while thread.is_alive():
            thread.join(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tiny multi-server automation tool.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", action="store_true", help=HELP["verbose"])
    subparsers = parser.add_subparsers(dest="tool")

    aws_parser = subparsers.add_parser(
        "ip", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    aws_parser.add_argument("--region", help=HELP["region"])
    aws_parser.add_argument("--public", action="store_true", help=HELP["public"])
    aws_parser.add_argument("kind", choices=("id", "asg", "elb"), help=HELP["kind"])
    aws_parser.add_argument("values", nargs="+", help=HELP["values"])

    run_parser = subparsers.add_parser(
        "run", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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

    get_parser = subparsers.add_parser(
        "get", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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

    put_parser = subparsers.add_parser(
        "put", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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
        sys.exit(1)
    return args


def main() -> int:
    # Avoid throwing exception on SIGPIPE.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if args.tool == "ip":
        print_ip_addrs(get_ip_addrs(args.values, args.kind, args.region), args.public)
        return 0
    else:
        for task in get_tasks(args):
            tasks.put_nowait(task)
        try:
            num_workers = min(args.threads, len(args.hosts))
            run_workers(num_workers)
        except KeyboardInterrupt:
            stop.set()
            log.info(red("terminating"))
    with lock:
        return len(args.hosts) - num_success


if __name__ == "__main__":
    sys.exit(main())
