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


def run(host, args):
    print(yellow(host) + " " + args.command)
    with fabric.Connection(
        host,
        user=args.user,
        connect_timeout=args.timeout,
        connect_kwargs={"key_filename": args.i},
    ) as c:
        (c.sudo if args.sudo else c.run)(args.command)


def ssh(args):
    threads = []
    for host in args.hosts:
        thread = threading.Thread(target=run, args=(host, args))
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
    ssh_parser.add_argument("--timeout", type=int, default=15)
    ssh_parser.add_argument("command")
    ssh_parser.add_argument("user")
    ssh_parser.add_argument("hosts", nargs="+")
    ssh_parser.set_defaults(func=ssh)

    try:
        args = parser.parse_args()
        args.func(args)
    except AttributeError:
        parser.print_help()


if __name__ == "__main__":
    main()
