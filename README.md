# 😽 kitten

[![Build Status](https://travis-ci.org/hoffa/kitten.svg?branch=master)](https://travis-ci.org/hoffa/kitten) [![Maintainability](https://api.codeclimate.com/v1/badges/34e6b84000b2ab0e1bce/maintainability)](https://codeclimate.com/github/hoffa/kitten/maintainability) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kitten.svg)](https://pypi.org/project/kitten) [![PyPI](https://img.shields.io/pypi/v/kitten.svg)](https://pypi.python.org/pypi/kitten) [![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fhoffa%2Fdamn.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fhoffa%2Fdamn?ref=badge_shield)

Tiny tool to manage multiple servers.

## Install

```
pip install kitten
```

If you haven't yet, install `awscli` and configure AWS credentials:

```
pip install awscli
aws configure
```

## Examples

Get IPs in Auto Scaling group:

```
$ kitten ip asg my-asg-name
18.105.107.20
34.229.135.48
```

Run command on all instances in the Auto Scaling group:

```
$ kitten ip asg my-asg-name | xargs kitten run uptime ubuntu
18.105.107.20 uptime
34.229.135.48 uptime
18.105.107.20 17:11:48 up 1 day,  6:02,  0 users,  load average: 0.91, 2.99, 3.49
34.229.135.48 17:11:48 up 5 days, 11:19,  0 users,  load average: 6.34, 5.94, 5.72
```

Commands are always run in parallel. Use `xargs`'s `-L` to not overwhelm your host.

Run command on 10 instances at a time:
```
$ kitten ip asg big-prod-asg | xargs -L 10 kitten run --sudo 'service nginx restart' ubuntu
```

Download file:
```
$ kitten ip elb big-prod-elb | xargs kitten get /var/log/system.log ubuntu
```

Upload file:
```
$ kitten ip elb big-prod-elb | xargs kitten put nginx.conf /etc/init/nginx.conf ubuntu
```
