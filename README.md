## `elasticsearch-tail.py`

rework of the earlier work by juan-domenech - thanks!! :)

only tested against opendistro for elasticsearch / with logstash syslog ingress

### Security !!1

all of the TLS verification checks have been removed

### Setup

python 3

`pip3 install -r requirements.txt`

### Config

copy the example-config.py to config.py and edit it 

If you have no auth set the elastic the user and pass to blank

set 'myindex' to eg logstash-foo

the tail 'sleep' sets the number of seconds between es requests

to disable colors set enabled to false

### Usage

run ./elasticsearch-tail.py
