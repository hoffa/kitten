#!/usr/bin/env python2
# coding = utf-8

import argparse
import re

import boto3


def find_ids(l):
    for s in l:
        for match in re.findall('[0-9a-f]{8,17}', s):
            yield 'i-' + match


def ids_to_ips(ids, region=None):
    client = boto3.client('ec2', region_name=region)
    for instance_id in find_ids(ids):
        try:
            for reservation in client.describe_instances(InstanceIds=[instance_id])['Reservations']:
                for instance in reservation['Instances']:
                    yield {'public_ip': instance.get('PublicIpAddress'),
                           'private_ip': instance.get('PrivateIpAddress')}
        except:
            pass


def asgs_to_ids(asgs, region=None):
    client = boto3.client('autoscaling', region_name=region)
    for asg in client.describe_auto_scaling_groups(AutoScalingGroupNames=asgs)['AutoScalingGroups']:
        for instance in asg['Instances']:
            yield instance['InstanceId']


def elbs_to_ids(elbs, region=None):
    client = boto3.client('elb', region_name=region)
    for elb in client.describe_load_balancers(LoadBalancerNames=elbs)['LoadBalancerDescriptions']:
        for instance in elb['Instances']:
            yield instance['InstanceId']


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('values', nargs='*')
    parser.add_argument('--from', help='input type', choices=['id', 'asg', 'elb'], default='id', dest='input')
    parser.add_argument('--to', help='output type', choices=['id', 'public_ip', 'private_ip'], default='public_ip', dest='output')
    parser.add_argument('--region', help='region')
    args = parser.parse_args()
    if args.input == 'id':
        ids = find_ids(args.values)
    elif args.input == 'asg':
        ids = asgs_to_ids(args.values, region=args.region)
    elif args.input == 'elb':
        ids = elbs_to_ids(args.values, region=args.region)
    if args.output == 'id':
        print ','.join(ids)
    else:
        ips = [ip[args.output] or ip['private_ip'] for ip in ids_to_ips(ids, region=args.region)]
        print ','.join(filter(None, ips))


if __name__ == '__main__':
    main()
