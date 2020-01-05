#!/usr/bin/env python3
import datetime
import sys
import ssl
from elasticsearch.connection import create_ssl_context
# disables SSL warnings
import warnings
warnings.filterwarnings("ignore")
import time as time2
import re
import signal
from elasticsearch import Elasticsearch
# local config
import config as cfg

# ctrlc
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
   return(cfg.tail_colors[color] + string  + '\x1b[0m ')
  else:
   return(string)

# get the index to be tailed
def get_index():
  indices = []
  list = es.indices.get_alias("*")

  # search for index from config file and append matches to list
  for index in list:
    index_name = str(cfg.myindex['name'])
    if re.match(('^' + index_name + '$'), index):
      indices = []
      indices.append(str(index))
      break
    if re.search(str(cfg.myindex['name']), index):
      indices.append(str(index))

  # no match found for supplied index
  if indices == []:
    print('no index found: ' + str(cfg.myindex['name']))
    sys.exit(1)

  # sort the list of indexes and return the latest
  indices = sorted(indices, reverse=True)
  return indices[0]

# Ctrl+C handler
signal.signal(signal.SIGINT, signal_handler)

# connect to es with no SSL security checks
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
print(print_c('red',index) + ' at ' +  print_c('blue',timestamp_short(latest_event_timestamp)))

# get current timestamp
current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])

# Main
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
      # time is the shorter format used in output
      timestamp = int(key['sort'][0])
      time = timestamp_short(timestamp)

      # default prog used for logstash
      prog = '_'

      # filebeat support
      if re.search('filebeat', cfg.myindex['name']):
        host = str(key['_source']['agent']['hostname'])
      else:
        host = str(key['_source']['logsource'])
        if key['_source']['program']:
          prog = str(key['_source']['program'])

      print(print_c('blue',time) + print_c('yellow', host) + print_c('green', prog) + message)
    # end of the results so set "current" timestamp to the last result
    current_time = timestamp
