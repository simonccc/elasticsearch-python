#!/usr/bin/env python3
import datetime
import sys
import ssl
from elasticsearch.connection import create_ssl_context
import warnings
warnings.filterwarnings("ignore")
import time as time2
import re
import signal
from elasticsearch import Elasticsearch
import config as cfg

# Ctrl+C
def signal_handler(signal, frame):
    sys.exit(0)

# get the latest doc in the index
def get_latest_event_timestamp(index):
    res = es.search(size=1, index=index, sort="@timestamp:desc", body={"query": {"match_all": {}} })

    # At least one event should return, otherwise we have an issue.
    if len(res['hits']['hits']) != 0:
        timestamp = res['hits']['hits'][0]['sort'][0]
        return timestamp
    else:
        print("ERROR: No results found in index="+index)
        sys.exit(1)

def search_events(then,now):
    query = {'query': {'bool': {'must': {'range': {'@timestamp': {'gt': then, 'lte': now }}}}}}
    res = es.search(size="1000", index=index, sort="@timestamp:asc", body=query)
    return res

def timestamp_short(timestamp):
    short = datetime.datetime.fromtimestamp(int(timestamp) / 1000).strftime('%H:%M:%S.%f')[:-3]
    return short

def print_c(color, string):
  if cfg.tail_colors['enabled'] == 'true': 
   return(cfg.tail_colors[color] + string  + '\x1b[0m')
  else:
   return(string)

# get the index to be tailed
def get_index():
    indices = []
    list = es.indices.get_alias("*")

    for index in list:

        # search for index from config file
        if re.search(str(cfg.myindex['name']), index):

          # if a match is found append it to list
          indices.append(str(index))

    # no match found for supplied index
    if indices == []:
        print('no index found: ' + str(cfg.myindex['name']))
        sys.exit(1)

    # sort the list of indexes
    indices = sorted(indices, reverse=True)

    # return the latest
    return indices[0]

# Ctrl+C handler
signal.signal(signal.SIGINT, signal_handler)

# http://elasticsearch-py.readthedocs.io/en/master/
# disable these if you don't need them!
ssl_context = create_ssl_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
es = Elasticsearch(
cfg.elastic['es_host'],
verify_certs=False,
ssl_context=ssl_context,
http_auth=(cfg.elastic['user'],cfg.elastic['pass']))

# get index
index = get_index()

# Get the latest event timestamp from the Index
latest_event_timestamp = get_latest_event_timestamp(index)
print('starting from: ' + print_c('red',index  + '-' +  str(timestamp_short(latest_event_timestamp))))

# get current timestamp
current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])

while True:

  # wait for logs..
  time2.sleep(cfg.tail['sleep'])

  # get latest ES timestamp
  latest_event_timestamp = get_latest_event_timestamp(index)

  # if latest ES timestamp is > now
  if ( int(latest_event_timestamp) > int(current_time)):

    # query ES for events between current time and latest
    results = search_events(int(current_time), int(latest_event_timestamp))

    # map dict of results
    for key in results['hits']['hits']:
      message = key['_source']['message']

      # timestamp from the last message in the result set is used for the next query
      timestamp = int(key['sort'][0])

      # convert timestamp into short time format used in output 
      time = timestamp_short(timestamp)

      # default prog used for logstash
      prog = 'NONE'

      # filebeat support
      if re.search('filebeat', cfg.myindex['name']):
        host = str(key['_source']['agent']['hostname'])
      else:
        host = str(key['_source']['logsource'])

        # prog
        if (key['_source']['program']) is not None:
          prog = str(key['_source']['program'])

      print('\x1b[1;33;94m' + time + '\x1b[0m ' + '\x1b[1;33;33m' + host +'\x1b[0m ' + '\x1b[1;33;92m' + prog + '\x1b[0m '  + message)

    # end of results so set "current" timestamp to the last result
    current_time = timestamp
