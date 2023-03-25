#!/usr/bin/env python3
import datetime, sys, ssl, re, signal, requests, socket

from retry import retry
requests.packages.urllib3.disable_warnings()
sys.tracebacklimit = 0

import time as time2

# elasticsearch
from opensearchpy import OpenSearch
from opensearchpy.connection import create_ssl_context

# local config
import config as cfg
es_host = cfg.elastic['es_host']
host = es_host.split(':')[1].replace("//", "")

# check dns exists
try:
  if socket.gethostbyname(host): pass
except:
  print('ERROR: no dns for:', host)
  sys.exit(1)

# ctrlc
def sig_h(signal, frame):
  sys.exit(0)
signal.signal(signal.SIGINT, sig_h)

# get the latest doc in the index
def get_latest_ts(index):

  res = es.search(size=1, index=index, sort="@timestamp:desc", body={"query": {"match_all": {}} })

  # At least one event should return
  if len(res['hits']['hits']) != 0:
    ts = int(res['hits']['hits'][0]['sort'][0])
    return ts
  else:
    print("ERROR: No results found in index="+index)
    sys.exit(1)

# search events between then and now
def search_events(then,now):
  query = {'query': {'bool': {'must': {'range': {'@timestamp': {'gt': then, 'lte': now }}}}}}
  res = es.search(size=cfg.tail['result_size'], index=index, sort="@timestamp:asc", body=query)
  return res

# return shortimestamp used in output
def ts_short(timestamp):
  return(datetime.datetime.fromtimestamp(int(timestamp) / 1000).strftime('%H:%M:%S.%f')[:-3])

# print output
def print_c(color, string):
  if cfg.tail_colors['enabled'] == 'true':
   return(cfg.tail_colors[color] + string  + '\x1b[0m ')
  else:
   return(string)

# get the index to be tailed
def get_index():

  # index name passed as an arg
  try:
    if sys.argv[1]:
      index_name = sys.argv[1]
  except:
    index_name = str(cfg.myindex['name'])

  indices = []
  list = es.indices.get(index_name + '*')

  # search for index from config file and append matches to list
  for index in list:

    # match an exact index if supplied
    if re.match(('^' + index_name + '$'), index):
      indices = []
      indices.append(str(index))
      break

    # search for index name in indexes
    if re.search(str(index_name), index):
      indices.append(str(index))

  # no match found for supplied index
  if indices == []:
    print('no index found: ' + str(index_name))
    sys.exit(1)

  # sort the list of indexes and return the latest one eg in the case of daily or monthly indexes
  return(sorted(indices, reverse=True)[0])

# connect to es with no SSL security checks
# disable these if you don't need them!
ssl_context = create_ssl_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
  es = OpenSearch(
  es_host,
#  verify_certs=False,
  ssl_context=ssl_context,
  http_auth=(cfg.elastic['user'],cfg.elastic['pass']))
except Exception as ex:
  print("Error:", ex)
  sys.exit(1)

# get index
index = get_index()

# Get the latest event timestamp from the Index
latest_ts = get_latest_ts(index)
print(print_c('red',index) + '- ' +  print_c('blue',ts_short(latest_ts)))

# get current timestamp
current_ts = int(datetime.datetime.now().strftime('%s%f')[:-3])

# Main
while True:

  # wait for logs..
  time2.sleep(float(cfg.tail['sleep']))

  # get latest ES timestamp
  latest_ts = get_latest_ts(index)

  # if latest ES timestamp is > now
  if ( latest_ts > current_ts):

    # query ES for events between current time and latest
    results = search_events(current_ts,latest_ts)

    # map dict of results
    for key in results['hits']['hits']:

      # logstash and filebeat
      try:
        message = key['_source']['message']
      except KeyError:
        try:
          message = key['_source']['log']
        except KeyError:
          pass

      # timestamp from the last message in the result set is used for the next query
      # time is the shorter format used in output
      latest_ts = int(key['sort'][0])
      time = ts_short(latest_ts)

      # filebeat support
      if re.search('filebeat',index):
        host = str(key['_source']['agent']['hostname'])
        prog = 'filebeat'
      else:

        # logstash syslog
        try:
          host = str(key['_source']['logsource'])
        except KeyError:
          try:
            host = str(key['_source']['host'])
          except KeyError:
            host = "*"

        # prog
        try:
          prog = str(key['_source']['program'])
        except KeyError:
          prog = "_"

      message = message.strip('\n')
      print(print_c('blue',time) + print_c('yellow', host) + print_c('green', prog) + message)
      time2.sleep(float(cfg.tail['buffer']))
      retry(delay=1)

    # end of the results so set "current" timestamp to the last result
    current_ts = latest_ts
