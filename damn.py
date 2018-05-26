#!/usr/bin/env python3

import argparse
import re

import boto3
from fabric import Connection


def yellow(s):
    return "\033[33m" + s + "\033[0m"


def find_ids(l):
    for s in l:
        for match in re.findall("[0-9a-f]{8,17}", s):
            yield "i-" + match


def ids_to_ips(ids, region=None):
    client = boto3.client("ec2", region_name=region)
    for instance_id in find_ids(ids):
        try:
            for reservation in client.describe_instances(InstanceIds=[instance_id])[
                "Reservations"
            ]:
                for instance in reservation["Instances"]:
                    yield {
                        "public-ip": instance.get("PublicIpAddress"),
                        "private-ip": instance.get("PrivateIpAddress"),
                    }
        except Exception:
            pass


def asgs_to_ids(asgs, region=None):
    client = boto3.client("autoscaling", region_name=region)
    for asg in client.describe_auto_scaling_groups(AutoScalingGroupNames=asgs)[
        "AutoScalingGroups"
    ]:
        for instance in asg["Instances"]:
            yield instance["InstanceId"]


def elbs_to_ids(elbs, region=None):
    client = boto3.client("elb", region_name=region)
    for elb in client.describe_load_balancers(LoadBalancerNames=elbs)[
        "LoadBalancerDescriptions"
    ]:
        for instance in elb["Instances"]:
            yield instance["InstanceId"]


def dispatch(command, host, user, connect_kwargs):
    print(f"running command on {host}")
    with Connection(host, user=user, connect_kwargs=connect_kwargs) as c:
        c.run(command)


def aws(args):
    if args.input == "id":
        ids = find_ids(args.values)
    elif args.input == "asg":
        ids = asgs_to_ids(args.values, region=args.region)
    elif args.input == "elb":
        ids = elbs_to_ids(args.values, region=args.region)
    if args.output == "id":
        print(" ".join(ids))
    else:
        ips = [
            ip[args.output] or ip["private-ip"]
            for ip in ids_to_ips(ids, region=args.region)
        ]
        print(" ".join(filter(None, ips)))


def ssh(args):
    print("bar", args)
    print(yellow("hosts: ") + " ".join(args.hosts))
    print(yellow("user: ") + args.user)
    print(yellow("command: ") + args.command)
    for host in args.hosts:
        dispatch(args.command, host, args.user, {"key_filename": args.i})


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    aws_parser = subparsers.add_parser("aws")
    aws_parser.add_argument("--region")
    aws_parser.add_argument("input", choices=("id", "asg", "elb"))
    aws_parser.add_argument("output", choices=("id", "public-ip", "private-ip"))
    aws_parser.add_argument("values", nargs="+")
    aws_parser.set_defaults(func=aws)

    ssh_parser = subparsers.add_parser("ssh")
    ssh_parser.add_argument("-i")
    ssh_parser.add_argument("--sudo", action="store_true")
    ssh_parser.add_argument("command")
    ssh_parser.add_argument("user")
    ssh_parser.add_argument("hosts", nargs="+")
    ssh_parser.set_defaults(func=ssh)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
