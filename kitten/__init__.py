#!/usr/bin/env python

from __future__ import unicode_literals

import argparse
import io
import os
import re
import sys
import threading

import boto3
import fabric

__version__ = "0.1.7"

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


def ip(values, kind, region_name, public):
    if kind == "id":
        ids = find_ids(values)
    elif kind == "asg":
        ids = asgs_to_ids(values, region_name=region_name)
    elif kind == "elb":
        ids = elbs_to_ids(values, region_name=region_name)
    for ip in ids_to_ips(ids, region_name=region_name):
        if public and ip["public"]:
            print(ip["public"])
        else:
            print(ip["private"])


def run(c, command, sudo):
    print("{} run {}".format(yellow(c.host), yellow(command)))
    f = io.StringIO()
    func = c.sudo if sudo else c.run
    func(command, out_stream=f, err_stream=f)
    for line in f.getvalue().splitlines():
        print(yellow(c.host) + " " + line)
    c.close()


def put(c, local, remote):
    print("{} put {} to {}".format(yellow(c.host), yellow(local), yellow(remote)))
    c.put(local, remote=remote)
    c.close()


def get(c, remote):
    try:
        os.mkdir(c.host)
    except OSError:
        pass
    local = c.host + "/" + os.path.basename(remote)
    print("{} get {} to {}".format(yellow(c.host), yellow(remote), yellow(local)))
    c.get(remote, local=local)
    c.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="tool")

    aws_parser = subparsers.add_parser("ip")
    aws_parser.add_argument("--region")
    aws_parser.add_argument("--public", action="store_true")
    aws_parser.add_argument("kind", choices=("id", "asg", "elb"))
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
        sys.exit(2)

    return args


def main():
    args = parse_args()
    if args.tool == "ip":
        ip(args.values, args.kind, args.region, args.public)
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
            threads = [
                threading.Thread(target=run, args=(c, args.command, args.sudo))
                for c in cs
            ]
        elif args.tool == "get":
            threads = [threading.Thread(target=get, args=(c, args.remote)) for c in cs]
        elif args.tool == "put":
            threads = [
                threading.Thread(target=put, args=(c, args.local, args.remote))
                for c in cs
            ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    main()
