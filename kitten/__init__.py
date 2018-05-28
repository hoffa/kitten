#!/usr/bin/env python

import argparse
import io
import os
import re
import threading

import boto3
import fabric


DEFAULT_TIMEOUT = 15


def yellow(s):
    return "\033[33m" + s + "\033[0m"


def find_ids(l):
    for s in l:
        for match in re.findall("[0-9a-f]{8,17}", s):
            yield "i-" + match


def ids_to_ips(ids, region_name=None):
    client = boto3.client("ec2", region_name=region_name)
    for instance_id in find_ids(ids):
        try:
            reservations = client.describe_instances(InstanceIds=[instance_id])
            for reservation in reservations["Reservations"]:
                for instance in reservation["Instances"]:
                    yield {
                        "public": instance.get("PublicIpAddress"),
                        "private": instance.get("PrivateIpAddress"),
                    }
        except Exception:
            pass


def asgs_to_ids(asg_names, region_name=None):
    client = boto3.client("autoscaling", region_name=region_name)
    asgs = client.describe_auto_scaling_groups(AutoScalingGroupNames=asg_names)
    for asg in asgs["AutoScalingGroups"]:
        for instance in asg["Instances"]:
            yield instance["InstanceId"]


def elbs_to_ids(elb_names, region_name=None):
    client = boto3.client("elb", region_name=region_name)
    elbs = client.describe_load_balancers(LoadBalancerNames=elb_names)
    for elb in elbs["LoadBalancerDescriptions"]:
        for instance in elb["Instances"]:
            yield instance["InstanceId"]


def ip(args):
    if args.type == "id":
        ids = find_ids(args.values)
    elif args.type == "asg":
        ids = asgs_to_ids(args.values, region_name=args.region)
    elif args.type == "elb":
        ids = elbs_to_ids(args.values, region_name=args.region)
    kind = "private" if args.private else "public"
    for ip in ids_to_ips(ids, region_name=args.region):
        print(ip[kind] or ip["private"])


def ssh_run(c, command, sudo):
    print("{} run {}".format(yellow(c.host), yellow(command)))
    f = io.StringIO()
    func = c.sudo if sudo else c.run
    func(command, out_stream=f, err_stream=f)
    for line in f.getvalue().splitlines():
        print(yellow(c.host) + " " + line)
    c.close()


def ssh_put(c, local, remote):
    print("{} put {} to {}".format(yellow(c.host), yellow(local), yellow(remote)))
    c.put(local, remote=remote)
    c.close()


def ssh_get(c, remote):
    try:
        os.mkdir(c.host)
    except OSError:
        pass
    local = c.host + "/" + os.path.basename(remote)
    print("{} get {} to {}".format(yellow(c.host), yellow(remote), yellow(local)))
    c.get(remote, local=local)
    c.close()


def start_threads(threads):
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def run(cs, command, sudo):
    start_threads(threading.Thread(target=ssh_run, args=(c, command, sudo)) for c in cs)


def get(cs, remote):
    start_threads(threading.Thread(target=ssh_get, args=(c, remote)) for c in cs)


def put(cs, local, remote):
    start_threads(threading.Thread(target=ssh_put, args=(c, local, remote)) for c in cs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version="0.1.5")
    subparsers = parser.add_subparsers(dest="tool")

    aws_parser = subparsers.add_parser("ip")
    aws_parser.add_argument("--region")
    aws_parser.add_argument("--private", action="store_true")
    aws_parser.add_argument("type", choices=("id", "asg", "elb"))
    aws_parser.add_argument("values", nargs="+")

    ssh_parser = subparsers.add_parser("run")
    ssh_parser.add_argument("-i")
    ssh_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ssh_parser.add_argument("--sudo", action="store_true")
    ssh_parser.add_argument("command")
    ssh_parser.add_argument("user")
    ssh_parser.add_argument("hosts", nargs="+")

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("-i")
    get_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    get_parser.add_argument("remote")
    get_parser.add_argument("user")
    get_parser.add_argument("hosts", nargs="+")

    put_parser = subparsers.add_parser("put")
    put_parser.add_argument("-i")
    put_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    put_parser.add_argument("local")
    put_parser.add_argument("remote")
    put_parser.add_argument("user")
    put_parser.add_argument("hosts", nargs="+")

    args = parser.parse_args()
    if not args.tool:
        parser.print_help()
    elif args.tool == "ip":
        ip(args)
    else:
        cs = [
            fabric.Connection(
                host,
                user=args.user,
                connect_timeout=args.timeout,
                connect_kwargs={"key_filename": args.i},
            )
            for host in args.hosts
        ]
        if args.tool == "run":
            run(cs, args.command, args.sudo)
        elif args.tool == "get":
            get(cs, args.remote)
        elif args.tool == "put":
            put(cs, args.local, args.remote)


if __name__ == "__main__":
    main()
