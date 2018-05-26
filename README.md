# 🚒 damn

[![Build Status](https://travis-ci.org/hoffa/damn.svg?branch=master)](https://travis-ci.org/hoffa/damn) [![Maintainability](https://api.codeclimate.com/v1/badges/c47c16854e850f077fbb/maintainability)](https://codeclimate.com/github/hoffa/awsutil/maintainability)

Easily manage multiple servers and automate tasks. Especially when production is burning.

![This is fine](https://i.imgur.com/ck8tvNd.png)

## Examples

Get IPs in Auto Scaling group:

```
$ ./damn.py aws asg my-asg-name
18.105.107.20
34.229.135.48
52.211.230.162
54.108.254.142
184.53.6.59
```

Run command:

```
$ ./damn.py ssh uptime ubuntu 18.105.107.20 34.229.135.48
18.105.107.20 uptime
34.229.135.48 uptime
 17:11:48 up 1 day,  6:02,  0 users,  load average: 0.91, 2.99, 3.49
 17:11:48 up 5 days, 11:19,  0 users,  load average: 6.34, 5.94, 5.72
```

Run command on 10 instances at a time:
```
$ ./damn.py aws asg big-prod-asg | xargs -L 10 ./damn.py ssh --sudo 'service nginx restart' ubuntu
```
