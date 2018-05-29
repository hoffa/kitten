#!/usr/bin/env python

from __future__ import unicode_literals

if sys.version_info.major > 2:
    import queue
else:
    import Queue as queue

import argparse
import functools
import os
import sys
import threading

import boto3
import fabric

__version__ = "0.1.18"

CHUNK_SIZE = 100
DEFAULT = {"timeout": 15, "threads": 10}
HELP = {
    "command": "shell command to execute",
    "hosts": "list of IP addresses",
    "i": "private key path",
    "kind": "AWS resource type",
    "local": "path to local file",
    "public": "print public IPs where possible",
    "region": "AWS region",
    "remote": "path to remote file",
    "sudo": "run command via sudo",
    "threads": "number of concurrent connections",
    "timeout": "connection timeout in seconds",
    "user": "remote connection user",
    "values": "list of instance IDs or resource names",
}

tasks = queue.Queue()


def red(s):
    return "\033[31m" + s + "\033[0m"


def yellow(s):
    return "\033[33m" + s + "\033[0m"


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def instance_ids_to_ips(resource, instance_ids):
    filters = [{"Name": "instance-id", "Values": instance_ids}]
    for instance in resource.instances.filter(Filters=filters):
        yield {
            "public": instance.public_ip_address,
            "private": instance.private_ip_address,
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


def print_ips(client, instance_ids, public, region_name):
    for chunk in chunks(list(instance_ids), CHUNK_SIZE):
        for ip in instance_ids_to_ips(client, chunk):
            print(public and ip["public"] or ip["private"])


def ip(values, kind, public, region_name):
    if kind == "id":
        instance_ids = values
    elif kind == "asg":
        autoscaling = boto3.client("autoscaling", region_name=region_name)
        instance_ids = asgs_to_instance_ids(autoscaling, values)
    elif kind == "elb":
        elb = boto3.client("elb", region_name=region_name)
        instance_ids = elbs_to_instance_ids(elb, values)
    ec2 = boto3.resource("ec2", region_name=region_name)
    print_ips(ec2, instance_ids, public, region_name)


def run(conn, command, sudo):
    print("{} run {}".format(yellow(conn.host), yellow(command)))
    with conn as c:
        func = c.sudo if sudo else c.run
        result = func(command, pty=True, hide=True, warn=True)
    for line in result.stdout.splitlines():
        if result.failed:
            line = red(line)
        print(yellow(conn.host) + " " + line)


def put(conn, local, remote):
    print("{} put {} to {}".format(yellow(conn.host), yellow(local), yellow(remote)))
    result = "ok"
    try:
        with conn as c:
            c.put(local, remote=remote)
    except Exception as e:
        result = red(str(e))
    print(yellow(conn.host) + " " + result)


def get(conn, remote):
    try:
        os.mkdir(conn.host)
    except OSError:
        pass
    local = conn.host + "/" + os.path.basename(remote)
    print("{} get {} to {}".format(yellow(conn.host), yellow(remote), yellow(local)))
    result = "ok"
    try:
        with conn as c:
            c.get(remote, local=local)
    except Exception as e:
        result = red(str(e))
    print(yellow(conn.host) + " " + result)


def worker():
    try:
        while True:
            task = tasks.get_nowait()
            task()
            tasks.task_done()
    except queue.Empty:
        pass


def start_workers(num_workers):
    for _ in range(num_workers):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()


def get_tasks(args):
    conns = [
        fabric.Connection(
            host,
            user=args.user,
            connect_timeout=args.timeout,
            connect_kwargs={"key_filename": args.i},
        )
        for host in args.hosts
    ]
    if args.tool == "run":
        return [functools.partial(run, conn, args.command, args.sudo) for conn in conns]
    elif args.tool == "get":
        return [functools.partial(get, conn, args.remote) for conn in conns]
    elif args.tool == "put":
        return [functools.partial(put, conn, args.local, args.remote) for conn in conns]


def parse_args():
    parser = argparse.ArgumentParser(description="Tiny multi-server automation tool.")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="tool")

    aws_parser = subparsers.add_parser("ip")
    aws_parser.add_argument("--region", help=HELP["region"])
    aws_parser.add_argument("--public", action="store_true", help=HELP["public"])
    aws_parser.add_argument("kind", choices=("id", "asg", "elb"), help=HELP["kind"])
    aws_parser.add_argument("values", nargs="+", help=HELP["values"])

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("-i", help=HELP["i"])
    run_parser.add_argument(
        "--timeout", type=int, default=DEFAULT["timeout"], help=HELP["timeout"]
    )
    run_parser.add_argument(
        "--threads", type=int, default=DEFAULT["threads"], help=HELP["threads"]
    )
    run_parser.add_argument("--sudo", action="store_true", help=HELP["sudo"])
    run_parser.add_argument("command", help=HELP["command"])
    run_parser.add_argument("user", help=HELP["user"])
    run_parser.add_argument("hosts", nargs="+", help=HELP["hosts"])

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("-i", help=HELP["i"])
    get_parser.add_argument(
        "--timeout", type=int, default=DEFAULT["timeout"], help=HELP["timeout"]
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
        "--timeout", type=int, default=DEFAULT["timeout"], help=HELP["timeout"]
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
    args = parse_args()
    if args.tool == "ip":
        ip(args.values, args.kind, args.public, args.region)
    else:
        for task in get_tasks(args):
            tasks.put_nowait(task)
        num_workers = min(args.threads, len(args.hosts))
        start_workers(num_workers)
        tasks.join()


if __name__ == "__main__":
    main()
