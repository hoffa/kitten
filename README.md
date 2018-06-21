<p align="center"><img alt="Kitten Logo" src="https://i.imgur.com/Rk3Vql3.png" height="150"></p>

# 😽 kitten

[![Build Status](https://travis-ci.org/hoffa/kitten.svg?branch=master)](https://travis-ci.org/hoffa/kitten) [![Maintainability](https://api.codeclimate.com/v1/badges/34e6b84000b2ab0e1bce/maintainability)](https://codeclimate.com/github/hoffa/kitten/maintainability) [![PyPI - Python Version](https://svgshare.com/i/6tK.svg)](https://pypi.org/project/kitten)

Tiny multi-server automation tool.

It's designed to be as simple as possible and play nice with Unix tools.

![Screenshot](https://i.imgur.com/QEQfOiv.png)

## Install

```Shell
pip install kitten
```

## Prerequisites

`kitten` can get IP addresses from AWS resources for you. For that you'll need to have your AWS credentials set up. You can do that using `awscli`:

```Shell
pip install awscli
```

Then:

```Shell
aws configure
```

## Examples

### Get IP addresses from AWS resources

Use `kitten ip` with either `id`, `asg`, `elb` or `opsworks`:

```Shell
$ kitten ip asg my-tiny-asg
18.135.117.17
24.129.235.48
```

- By default only private IP addresses are returned. Use `--public` if you prefer public IPs.
- You can change region using `--region`.

If you're in a hurry, you just paste any text that contains instance IDs:

```Shell
$ kitten ip id prod-mongo-0901bc21990109ed4-eu my-hostname-06a2fc734534ef6d9
17.136.127.18
23.119.136.38
```

### Run command on servers

Use `kitten run`:

```Shell
$ kitten run uptime ubuntu 18.105.107.20 34.229.135.48
18.105.107.20	run	uptime
34.229.135.48	run	uptime
18.105.107.20	17:11:48 up 1 day,  6:02,  0 users,  load average: 0.91, 2.99, 3.49
34.229.135.48	17:11:48 up 5 days, 11:19,  0 users,  load average: 6.34, 5.94, 5.72
```

- Replace `ubuntu` with the user used to log in on the servers.
- Use `-i` to specify a private key. Otherwise, behavior is similar to [`ssh`](http://man7.org/linux/man-pages/man1/ssh.1.html).
- Commands are always run in parallel. Use `--threads` to specify the maximum number of concurrent connections (defaults to 10).
- Use `--sudo` to run commands via `sudo`.

Just pipe `kitten ip` to [`xargs`](http://man7.org/linux/man-pages/man1/xargs.1.html) to do everything in one step.

### Download files from servers

Use `kitten get`:

```Shell
kitten ip opsworks a283c671-d4c1-4dfa-a7c2-823b7f7b2c2c | xargs kitten get /tmp/system.log ubuntu
```

### Upload file to servers

Use `kitten put`:

```Shell
kitten ip asg big-prod-asg | xargs kitten put -i ~/.ssh/key.pem cat.jpg /root/cat.jpg root
```
