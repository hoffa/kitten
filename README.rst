kitten |travis|
===============

.. |travis| image:: https://github.com/hoffa/kitten/workflows/.github/workflows/workflow.yml/badge.svg
   :target: https://github.com/hoffa/kitten/actions

Tiny multi-server automation tool.

Run command on multiple servers. Designed to be as simple as possible and play nice with Unix tools.

.. image:: https://i.imgur.com/QEQfOiv.png

Installation
------------

::

  pip install kitten

Prerequisites
-------------

``kitten`` can get IP addresses from AWS resources for you. For that you'll need to have your AWS credentials set up.
You can do that using ``awscli``:

::

  pip install awscli

Then:

::

  aws configure

Examples
--------

Run command on servers
~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten run``:

::

  $ kitten run uptime ubuntu 18.105.107.20 34.229.135.48
  18.105.107.20	run	uptime
  34.229.135.48	run	uptime
  18.105.107.20	17:11:48 up 2 days,  6:02,  0 users,  load average: 0.91, 2.99, 3.49
  34.229.135.48	17:11:48 up 5 days, 11:19,  0 users,  load average: 6.34, 5.94, 5.72

- Replace ``ubuntu`` with the user used to log in on the servers
- Use ``-i`` to specify a private key
- Use ``--threads`` to specify the number of concurrent connections (defaults to 10)

Get IP addresses from AWS resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten ip`` with either ``id``, ``asg`` or ``elb``:

::

  $ kitten ip asg my-tiny-asg
  18.135.117.17
  24.129.235.48

- By default only private IP addresses are returned. Use ``--public`` if you prefer public IPs
- You can change region using ``--region``

If you're in a hurry, you can just paste any text that contains instance IDs:

::

  $ kitten ip id prod-mongo-0901bc21990109ed4-eu my-hostname-06a2fc734534ef6d9
  17.136.127.18
  23.119.136.38

Download files from servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten get``:

::

  kitten ip elb my-load-balancer | xargs kitten get /tmp/system.log ubuntu

Upload file to servers
~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten put``:

::

  kitten ip asg big-prod-asg | xargs kitten put -i ~/.ssh/key.pem cat.jpg /tmp ubuntu
