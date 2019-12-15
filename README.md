## `elasticsearch-tail.py`

implementation of a tail like thing for Elasticsearch 7.x

### Setup 

Only tested on Python 3

pip3 install -r requirements.txt

### Usage

The only mandatory parameter is `--endpoint`.

Example:
`python elasticsearch-tail.py --endpoint http://elak.example.com`

By default last 10 lines of log are displayed. You can change this behaviour with `--docs` or `-n` switch.

Example:

`python elasticsearch-tail.py --endpoint http://elak.example.com -n 50`

By default the latest Logstash Index available is used. Optionally you can specify the desired index name.

Example:

`python elasticsearch-tail.py --endpoint http://elak.example.com --index logstash-2016.08.08`

To have continuous output use `-f` or `--nonstop`.

Example:

`python elasticsearch-tail.py --endpoint http://elak.example.com -f`

To display the native ES timestamp of each event use `--showheaders`.

Example:

`python elasticsearch-tail.py --endpoint http://elak.example.com --showheaders`

To display events belonging to a particular host and ignore the rest use `--hostname`.

Example:

`python elasticsearch-tail.py --endpoint http://elak.example.com --hostname server1.example.com`
