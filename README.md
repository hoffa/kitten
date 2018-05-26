# 🚒 awsutil

[![Build Status](https://travis-ci.org/hoffa/damn.svg?branch=master)](https://travis-ci.org/hoffa/damn) [![Maintainability](https://api.codeclimate.com/v1/badges/c47c16854e850f077fbb/maintainability)](https://codeclimate.com/github/hoffa/awsutil/maintainability)

Easily manage multiple servers and automate tasks. Especially when production is burning.

![This is fine](https://i.imgur.com/ck8tvNd.png)

## Getting started

Install the dependencies:

```
pip install awscli fabric boto3
```

Set up AWS credentials and default region:
```
aws configure
```

You might also want to add something similar to your aliases:
```
alias awsutil='~/Code/awsutil/awsutil'
alias fabutil='fab --skip-bad-hosts --warn-only -f ~/Code/awsutil/fabfile.py'
```

* [`awsutil`](awsutil) allows you to convert from AWS resources (instances, ASGs and ELBs) to a list of instance IDs/IPs.
* [`fabutil`](fabfile.py) allows you to execute commands on multiple servers.

## Using `awsutil`

* Get IPs from instance IDs:

    ```
    $ awsutil i-ff9b72e46eaddbb87 i-965ff8b526ba83f8e
    12.123.234.5,23.123.234.123
    ```

* You can also pass any messy text (e.g. quickly copied from a log) and it will automatically find the instance IDs:

    ```
    $ awsutil host-a-ff9b72e46eaddbb87-b host-b-965ff8b526ba83f8e-c
    12.123.234.5,23.123.234.123
    ```

* Works also for ASGs and ELBs:

    ```
    $ awsutil --from asg prod-content-server
    12.123.234.5,23.123.234.123
    ```

    ```
    $ awsutil --from elb prod-process-external
    12.123.234.5,23.123.234.123
    ```

* By default, `awsutil` will print public IPs whenever possible (private IP otherwise). Use `--to` to adjust output format:

    ```
    $ awsutil --to private-ip host-a-ff9b72e46eaddbb87-b host-b-965ff8b526ba83f8e-c
    10.20.123.1,10.20.123.2
    ```

    ```
    $ awsutil --from elb --to id prod-process-external
    i-ff9b72e46eaddbb87 i-965ff8b526ba83f8e
    ```

## Using `fabutil`

`fabutil` is just a tiny layer over vanilla [Fabric](http://www.fabfile.org). It allows you to execute commands on a list a servers.

As a silly example, to see a server's uptime, you could do:

```
$ fabutil run:uptime -H 12.123.234.5 -u ubuntu
[12.123.234.5] out:  08:18:25 up 19:28,  1 user,  load average: 2.83, 3.62, 3.55
```

Here's a slightly more realistic example:

```
$ fabutil \
  -H `awsutil --from asg prod-content-server` \
  -u ubuntu \
  -i ~/.ssh/id_rsa.prod \
  sudo:"sed -i s/10.20.123.1/10.20.123.255/g /etc/server.conf && service server restart"
```

By default, `fabutil` will skip unreachable hosts and only warn if a command fails.

Check out the [Fabric docs](http://docs.fabfile.org/en/1.14/usage/fab.html) for a list of supported command-line arguments. The most useful ones are probably [`-H`](http://docs.fabfile.org/en/1.14/usage/fab.html#cmdoption-H), [`-u`](http://docs.fabfile.org/en/1.14/usage/fab.html#cmdoption-u), [`-i`](http://docs.fabfile.org/en/1.14/usage/fab.html#cmdoption-i) and [`--parallel`](http://docs.fabfile.org/en/1.14/usage/fab.html#cmdoption-P).

## Options

```
$ awsutil -h                     
usage: awsutil [-h] [--from {id,asg,elb}] [--to {id,public_ip,private_ip}]
              [--region REGION]
              [values [values ...]]

positional arguments:
  values

optional arguments:
  -h, --help                     show this help message and exit
  --from {id,asg,elb}            input type (default: id)
  --to {id,public-ip,private-ip} output type (default: public-ip)
  --region REGION                region (default: None)
```

```
$ fabutil --list                       
Available commands:                

    get   <path> Download file     
    put   <local-path>,<remote-path> Upload file                       
    run   <command> Run command    
    sudo  <command> Run command as root
```
