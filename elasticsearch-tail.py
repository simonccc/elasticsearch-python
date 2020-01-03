#!/usr/bin/env python3
import datetime
import sys
import ssl
from elasticsearch.connection import create_ssl_context
import warnings
warnings.filterwarnings("ignore")
import time as time2
import threading
# from random import randint
import platform
import re
import signal
from elasticsearch import Elasticsearch
import config as cfg

# Ctrl+C
def signal_handler(signal, frame):
    sys.exit(0)

def from_epoch_milliseconds_to_string(epoch_milli):
    return str(datetime.datetime.utcfromtimestamp( float(str( epoch_milli )[:-3]+'.'+str( epoch_milli )[-3:]) ).strftime('%Y-%m-%dT%H:%M:%S.%f'))[:-3]+"Z"

def from_epoch_seconds_to_string(epoch_secs):
    return from_epoch_milliseconds_to_string(epoch_secs * 1000)

def from_string_to_epoch_milliseconds(string):
    epoch = datetime.datetime(1970, 1, 1)
    pattern = '%Y-%m-%dT%H:%M:%S.%fZ'
    milliseconds =  int(str(int((datetime.datetime.strptime(from_date_time, pattern) - epoch).total_seconds()))+from_date_time[-4:-1])
    return milliseconds

def get_latest_event_timestamp(index):
    res = es.search(size=1, index=index, sort="@timestamp:desc", body={"query": {"match_all": {}} })

    # At least one event should return, otherwise we have an issue.
    if len(res['hits']['hits']) != 0:
        timestamp = res['hits']['hits'][0]['sort'][0]
        return timestamp
    else:
        print ("ERROR: get_latest_event_timestamp: No results found in index="+index)
        sys.exit(1)

# Inserts event into event_pool{}
def to_object(res):

    for hit in res['hits']['hits']:
        message= str(hit['_source']['message'])
        id = str(hit['_id'])
        timestamp = str(hit['sort'][0])

        # filebeat
        if re.search('filebeat', cfg.myindex['name']):
            host = str(hit['_source']['agent']['hostname'])
            event_pool[id] = { 'timestamp': timestamp, 'host': host, 'message': message }
        else:
        # assume logstash format as default
            host = str(hit['_source']['logsource'])
            if (hit['_source']['program']) is not None:
              prog = str(hit['_source']['program'])
            else:
                prog = 'NONE'
            event_pool[id] = { 'timestamp': timestamp, 'host': host, 'prog': prog,'message': message }
    return

def purge_event_pool(event_pool):

    to_print = []

    for event in event_pool.copy():
        event_timestamp = int(event_pool[event]['timestamp'])
        # if event_timestamp >= current time pointer and < (current time pointer + the gap covered by interval):
        # if event_timestamp >= ten_seconds_ago and (event_timestamp < ten_seconds_ago + interval):
        # if event_timestamp <= oldest_in_the_pool + interval:
        if event_timestamp >= (ten_seconds_ago - interval) and event_timestamp < ten_seconds_ago:
            # Print and...
            event_to_print = event_pool[event]
            # adding event ID
            event_to_print['id'] = event
            to_print.append(event_pool[event])
            # delete...
            event_pool.pop(event)
        elif event_timestamp < ten_seconds_ago - interval:
            # ...discard what is below last output.
            event_pool.pop(event)

    # Sort by timestamp
    def getKey(item):
        return item['timestamp']

    # Print (add to print_pool) and let wait() function to print it out later
    for event in sorted(to_print,key=getKey):

       # my current filebeat logs include date + hostname
       if re.search('filebeat', cfg.myindex['name']):
         print_pool.append(event['message'] + '\n')
       # logstash / default include data and logsource
       else:
         dt = datetime.datetime.fromtimestamp(int(event['timestamp']) / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         print_pool.append('\x1b[1;33;94m' + dt + '\x1b[0m ' + '\x1b[1;33;33m' + event['host'] + '\x1b[0m ' + '\x1b[1;33;92m' + event['prog'] + '\x1b[0m '  + event['message'] + '\n')

    return

def search_events(from_date_time):
    query_search['query']['bool']['must'] = {"range": {"@timestamp": {"gte": from_date_time}}}
    res = es.search(size="1000", index=index, sort="@timestamp:asc", body=query_search)
    return res

def wait(milliseconds):
    current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])
    final_time = current_time + milliseconds
    len_print_pool = len(print_pool)

    while final_time > current_time:
        current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])
        what_to_do_while_we_wait()
        time2.sleep(.01)

def what_to_do_while_we_wait():
    global print_pool
    len_print_pool_2 = len( print_pool )
    wait_interval = interval + .0

    for i in range(0,len_print_pool_2 ):
        sys.stdout.write( print_pool[i] )
        sys.stdout.flush()

    print_pool = []


# Get lastest available index
def check_index():

    # Get indices list
    indices = []
    list = es.indices.get_alias("*")
    for index in list:
        if index[0:9] == str(cfg.myindex['name'] + '-'):
            indices.append(str(index))
    if indices == []:
        print('no index ' + str(cfg.myindex['name']))
        sys.exit(1)
    indices = sorted(indices, reverse=True)
    return indices[0]

def thread_execution(from_date_time):
    res = search_events(from_date_time)
    to_object(res)
    return

class Threading (threading.Thread):
    def __init__(self, threadID, name, from_date_time):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.from_date_time = from_date_time
    def run(self):
        thread_execution(self.from_date_time)
        del self

### Main

# Ctrl+C handler
signal.signal(signal.SIGINT, signal_handler)

interval = 100  # milliseconds

event_pool = {}

print_pool = []

to_the_past = 1000  # milliseconds

# Mutable query object base for main search
query_search = {
"query": {
  "bool": {
    "must": [
    {
      "range": {}
     }
    ],
  }
 }
}

# http://elasticsearch-py.readthedocs.io/en/master/
ssl_context = create_ssl_context()

# disable these if you don't need them!
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# and fix this
es = Elasticsearch(cfg.elastic['es_host'],verify_certs=False,ssl_context=ssl_context,http_auth=(cfg.elastic['user'],cfg.elastic['pass']))

# get index
index = check_index()

# Get the latest event timestamp from the Index
latest_event_timestamp = get_latest_event_timestamp(index)

# Go 10 seconds to the past. There is where we place "in the past" pointer to give time to ES to consolidate its index.
ten_seconds_ago = latest_event_timestamp - to_the_past
thread = Threading(1,"Thread-1", ten_seconds_ago)

while True:

    # From timestamp in milliseconds to Elasticsearch format (seconds.milliseconds). i.e: 2016-07-14T13:37:45.123Z
    from_date_time = from_epoch_milliseconds_to_string(ten_seconds_ago)

    if not thread.isAlive():
        thread = Threading(1,"Thread-1", from_date_time)
        thread.start()

    # "Send to print" and purge oldest events in the pool
    purge_event_pool(event_pool)

    # Wait for Elasticsearch to index a bit more of stuff and Print meanwhile
    wait(interval)

    # Move the 'past' pointer one 'interval' ahead
    ten_seconds_ago += interval
