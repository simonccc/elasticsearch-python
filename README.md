## `elasticsearch-tail.py`

implementation of a tail like thing for elasticsearch 7.x

simplification of the earlier work by juan-domenech - thanks!! :) 

tested against the open distro for elasticsearch 1.3.x

### Security

all of the TLS verification checks have been removed - have a look at the code; they should be easy to re-enable

### Setup

python 3 required

pip3 install -r requirements.txt

### Usage

create a config.py based on the example provided

logstash and filebeat are the only index patterns tested so far! ymmv
you do not need to include a trailing '-' on the index

then run ./elasticsearch-tail.py

