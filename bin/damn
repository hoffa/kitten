#!/usr/bin/env python

import argparse
import re
import threading

import boto3
import fabric


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
            for reservation in client.describe_instances(InstanceIds=[instance_id])[
                "Reservations"
            ]:
                for instance in reservation["Instances"]:
                    yield {
                        "public": instance.get("PublicIpAddress"),
                        "private": instance.get("PrivateIpAddress"),
                    }
        except Exception:
            pass


def asgs_to_ids(asgs, region_name=None):
    client = boto3.client("autoscaling", region_name=region_name)
    for asg in client.describe_auto_scaling_groups(AutoScalingGroupNames=asgs)[
        "AutoScalingGroups"
    ]:
        for instance in asg["Instances"]:
            yield instance["InstanceId"]


def elbs_to_ids(elbs, region_name=None):
    client = boto3.client("elb", region_name=region_name)
    for elb in client.describe_load_balancers(LoadBalancerNames=elbs)[
        "LoadBalancerDescriptions"
    ]:
        for instance in elb["Instances"]:
            yield instance["InstanceId"]


def aws(args):
    if args.type == "id":
        ids = find_ids(args.values)
    elif args.type == "asg":
        ids = asgs_to_ids(args.values, region_name=args.region)
    elif args.type == "elb":
        ids = elbs_to_ids(args.values, region_name=args.region)
    kind = "private" if args.private else "public"
    for ip in ids_to_ips(ids, region_name=args.region):
        print(ip[kind] or ip["private"])


def run(host, user, connect_kwargs, command, sudo):
    print(yellow(host) + " " + command)
    with fabric.Connection(host, user=user, connect_kwargs=connect_kwargs) as c:
        if sudo:
            c.sudo(command)
        else:
            c.run(command)


def ssh(args):
    threads = []
    for host in args.hosts:
        thread = threading.Thread(
            target=run,
            args=(host, args.user, {"key_filename": args.i}, args.command, args.sudo),
        )
        thread.start()
    for thread in threads:
        thread.join()


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    aws_parser = subparsers.add_parser("aws")
    aws_parser.add_argument("--region")
    aws_parser.add_argument("--private", action="store_true")
    aws_parser.add_argument("type", choices=("id", "asg", "elb"))
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
