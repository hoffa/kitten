kitten |travis|
===============

.. |travis| image:: https://travis-ci.org/hoffa/kitten.svg?branch=master
   :target: https://travis-ci.org/hoffa/kitten

작은 다중 서버 자동화 도구.

여러 서버에서 명령을 실행하십시오. 가능한 한 간단하고 유닉스툴 로 멋진 플레이를 할 수 있도록 설계됨.

.. image:: https://i.imgur.com/QEQfOiv.png

설치
------------

::

  pip install kitten

전제조건
-------------

``kitten``은 AWS 자원으로부터 IP 주소를 얻을 수 있다. 그러기 위해서는 AWS 자격 증명을 설정해야 할 것이다. 당신은 ``awscli``를 사용하여 그것을 할 수 있다.

::

  pip install awscli

그런 다음:

::

  aws configure

예
--------

서버에서 명령 실행
~~~~~~~~~~~~~~~~~~~~~~

 ``kitten run``을 사용하십시오 :

::

  $ kitten run uptime ubuntu 18.105.107.20 34.229.135.48
  18.105.107.20	run	uptime
  34.229.135.48	run	uptime
  18.105.107.20	17:11:48 up 2 days,  6:02,  0 users,  load average: 0.91, 2.99, 3.49
  34.229.135.48	17:11:48 up 5 days, 11:19,  0 users,  load average: 6.34, 5.94, 5.72

- ``ubuntu``를 서버에 로그인하는 데 사용되는 사용자로 대체해라
- 개인 키를 지정하려면 ``-i``를 사용하십시오.
- 동시 연결 수를 지정하려면 ``--threads``를 사용하십시오(기본값은 10).

AWS 리소스에서 IP 주소 가져오기
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``kitten ip``을 ``id``, ``asg``, ``elb`` or ``opsworks``와 함게 사용해라:

::

  $ kitten ip asg my-tiny-asg
  18.135.117.17
  24.129.235.48

- 기본적으로 오직 사설 IP 주소만 반환된다. 공인 IP를 선호하는 경우 ``--public``을 사용하십시오.
- ``--지역``을 사용하여 지역을 변경할 수 있다.

급할 경우 인스턴스 ID가 들어 있는 텍스트를 붙여넣기만 하면 된다.
::

  $ kitten ip id prod-mongo-0901bc21990109ed4-eu my-hostname-06a2fc734534ef6d9
  17.136.127.18
  23.119.136.38

Download files from servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten get``:

::

  kitten ip opsworks a283c671-d4c1-4dfa-a7c2-823b7f7b2c2c | xargs kitten get /tmp/system.log ubuntu

Upload file to servers
~~~~~~~~~~~~~~~~~~~~~~

Use ``kitten put``:

::

  kitten ip asg big-prod-asg | xargs kitten put -i ~/.ssh/key.pem cat.jpg /tmp ubuntu
