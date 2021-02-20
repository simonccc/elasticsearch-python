## `elasticsearch-tail.py`

rework of the earlier work by juan-domenech - thanks!! :)

only tested against: 
  * opendistro 7.x-oss / with logstash syslog ingress
  * oss 6.x using eg filebeat to logstash type setups

### Security !!1

all of the TLS verification checks have been removed

### Setup

python 3

`pip3 install -r requirements.txt`

### Config

copy the example-config.py to config.py and edit it 

set the user and pass to '' if you don't need auth

* `myindex` set this to eg logstash-foo and it will find the latest index based on that pattern 

* `sleep` sets the number of seconds between es requests

* `buffer` is the delay between printing each line

* `result_size` is how many docs we pull back per request

you may need to tweak these depending on how many docs you're expecting / how loaded ES is

* `tail_color` section to disable colors set 'enabled' to false

### Usage

run ./elasticsearch-tail.py
