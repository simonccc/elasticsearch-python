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
        dt = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
#        print('from: \x1b[1;33;94m' + str(dt) + '\x1b[0m')
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
    prog = 'NONE'

    # filebeat
    if re.search('filebeat', cfg.myindex['name']):
      host = str(hit['_source']['agent']['hostname'])
      event_pool[id] = { 'timestamp': timestamp, 'host': host, 'message': message }
    else:
      # assume logstash format as default
      host = str(hit['_source']['logsource'])
      if (hit['_source']['program']) is not None:
        prog = str(hit['_source']['program'])

      event_pool[id] = { 'timestamp': timestamp, 'host': host, 'prog': prog,'message': message }
    return

def search_events(then,now):
    query_search['query']['bool']['must'] = {"range": {"@timestamp": {"gte": then, "lte": now}}}
    res = es.search(size="1000", index=index, sort="@timestamp:asc", body=query_search)
    return res

# Get lastest available index
def check_index():

    indices = []
    list = es.indices.get_alias("*")
    for index in list:
        if re.search(str(cfg.myindex['name']), index):
          indices.append(str(index))
    if indices == []:
        print('no index ' + str(cfg.myindex['name']))
        sys.exit(1)
    indices = sorted(indices, reverse=True)
    print('Tailing \x1b[1;33;91m' + indices[0] + '\x1b[0m')
    return indices[0]

# Ctrl+C handler
signal.signal(signal.SIGINT, signal_handler)

#query object base for main search
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
current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])

while True:

  # get latest ES timestamp
  latest_event_timestamp = get_latest_event_timestamp(index)

  # if latest ES timestamp is > now
  if ( int(latest_event_timestamp) > int(current_time)):

    # query ES for events between current time and latest
    results = search_events(int(current_time), int(latest_event_timestamp))

    # map dict of results
    for key in results['hits']['hits']:

      message= str(key['_source']['message'])
      id = str(key['_id'])
      timestamp = str(key['sort'][0])
      dt = datetime.datetime.fromtimestamp(int(timestamp) / 1000).strftime('%H:%M:%S.%f')[:-3]
      prog = 'NONE'

      # filebeat
      if re.search('filebeat', cfg.myindex['name']):
        host = str(key['_source']['agent']['hostname'])
      else:
      # assume logstash format as default
        host = str(key['_source']['logsource'])
        if (key['_source']['program']) is not None:
          prog = str(key['_source']['program'])

      print('\x1b[1;33;94m' + dt + '\x1b[0m ' + '\x1b[1;33;33m' + host +'\x1b[0m ' + '\x1b[1;33;92m' + prog + '\x1b[0m '  + message)

    # end of results so set "current" timestamp to the last result
    current_time = timestamp

  time2.sleep(0.5)
