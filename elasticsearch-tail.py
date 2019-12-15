#!/usr/bin/env python3
import datetime
import sys
import ssl
from elasticsearch.connection import create_ssl_context
import warnings
warnings.filterwarnings("ignore")
import time as time2
from argparse import ArgumentParser
import threading
# from random import randint
import platform
import re
import signal # Dealing with Ctrl+C
from elasticsearch import Elasticsearch

# Arguments parsing
parser = ArgumentParser(description='Unix like tail command for Elastisearch')
parser.add_argument('-e', '--endpoint', help='ES endpoint URL.', required=True)
parser.add_argument('-i', '--index', help='Index name. If none then "filebeat-*" will be used.')
parser.add_argument('-o', '--hostname', help='Hostname to search (optional).')
parser.add_argument('-l', '--javalevel', help='Java Level.')
parser.add_argument('-j', '--javaclass', help='Java Class.')
parser.add_argument('-r', '--httpresponse', help='HTTP Server Response.')
parser.add_argument('-m', '--httpmethod', help='HTTP Request Method.')
parser.add_argument('-f', '--nonstop', help='Non stop. Continuous tailing.', action="store_true")
parser.add_argument('-n', '--docs', help='Number of documents.', default=10)
parser.add_argument('-s', '--showheaders', help='Show @timestamp, hostname fields in the output.', action="store_true")
args = parser.parse_args()

# Ctrl+C
def signal_handler(signal, frame):
    sys.exit(0)

def normalize_endpoint(endpoint):
    end_with_number = re.compile(":\d+$")

    if endpoint[-1:] == '/':
        endpoint = endpoint[:-1]

    if endpoint[0:5] == "http:" and not end_with_number.search(endpoint):
        endpoint = endpoint+":80"
        return endpoint

    if endpoint[0:6] == "https:" and not end_with_number.search(endpoint):
        endpoint = endpoint+":443"
        return endpoint

    if not end_with_number.search(endpoint):
        endpoint = endpoint+":80"
        return endpoint

    return endpoint


def from_epoch_milliseconds_to_string(epoch_milli):
    return str(datetime.datetime.utcfromtimestamp( float(str( epoch_milli )[:-3]+'.'+str( epoch_milli )[-3:]) ).strftime('%Y-%m-%dT%H:%M:%S.%f'))[:-3]+"Z"


def from_epoch_seconds_to_string(epoch_secs):
    return from_epoch_milliseconds_to_string(epoch_secs * 1000)


def from_string_to_epoch_milliseconds(string):
    epoch = datetime.datetime(1970, 1, 1)
    pattern = '%Y-%m-%dT%H:%M:%S.%fZ'
    milliseconds =  int(str(int((datetime.datetime.strptime(from_date_time, pattern) - epoch).total_seconds()))+from_date_time[-4:-1])
    return milliseconds


def get_latest_event_timestamp_dummy_load(index):
    # Return current time as fake lastest event in ES
    timestamp = int(datetime.datetime.utcnow().strftime('%s%f')[:-3]) - 20000
    return timestamp


def get_latest_event_timestamp(index):
    if host_to_search or value1:
        res = es.search(size=1, index=index, fields="@timestamp", sort="@timestamp:desc",
                        body=query_latest)
    else:
        res = es.search(size=1, index=index, fields="@timestamp", sort="@timestamp:desc",
                        body={
                            "query":
                                {"match_all": {}}
                        }
                        )

    # At least one event should return, otherwise we have an issue.
    if len(res['hits']['hits']) != 0:
        timestamp = res['hits']['hits'][0]['sort'][0]
        return timestamp
    else:
        print ("ERROR: get_latest_event_timestamp: No results found with the current search criteria under index="+index)
        print ("INFO: Please use --index or --hostname")
        sys.exit(1)


# When we are under -f --nonstop
def get_latest_events(index): # And print them

    if host_to_search or value1:
        res = es.search(size=docs, index=index,
                        sort="@timestamp:desc",
                        body=query_latest)
    else:
        res = es.search(size=docs, index=index,
                        sort="@timestamp:desc",
                        body={
                            "query":
                                {"match_all": {}}
                        }
                        )

    # At least one event should return, otherwise we have an issue.
    if len(res['hits']['hits']) != 0:
        timestamp = res['hits']['hits'][0]['sort'][0]
        to_object(res)
        single_run_purge_event_pool(event_pool)
        return timestamp # Needed???
    else:
        print ("ERROR: get_latest_events: No results found with the current search criteria under index="+index)
        print ("INFO: Please use --index, --type or --hostname")
        sys.exit(1)


# Inserts event into event_pool{}
def to_object(res):

    for hit in res['hits']['hits']:
        message= str(hit['_source']['message'])
        host = str(hit['_source']['agent']['hostname'])
        id = str(hit['_id'])
        timestamp = str(hit['sort'][0])
        event_pool[id] = { 'timestamp': timestamp, 'host': host, 'message': message }

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
        # print_event_by_event(event)
        if show_headers:
            print_pool.append(from_epoch_milliseconds_to_string(event['timestamp']) + " " + event['id'] + " " + event['host'] + " "  + event['message'] + '\n')
        else:
            print_pool.append(event['message'] + '\n')
    return


def single_run_purge_event_pool(event_pool):
    # global event_pool
    global print_pool
    to_print = []

    for event in event_pool:
        to_print.append(event_pool[event])

    # Sort by timestamp
    def getKey(item):
        return item['timestamp']

    for event in sorted(to_print, key=getKey):
        if show_headers:
            print_pool.append(
                from_epoch_milliseconds_to_string(event['timestamp']) + " " + event['host'] + " " + event['message'] + '\n')
        else:
            print_pool.append(event['message'] + '\n')

    what_to_do_while_we_wait()
    # print_pool = []
    # event_pool = {}


def query_test(from_date_time):
    # global event_pool
    # global print_pool
    # to_print = []

    query_search = { "query": {
                            "filtered": {
                                "query": {
                                    "bool": {
                                        "must": [ ]
                                    }
                                },
                                "filter": {
                                    "range": { }
                                }
                            }
                        }
                    }

    query_search['query']['filtered']['filter']['range'] = {"@timestamp": {"gte": from_date_time}}
    query_search['query']['filtered']['query']['bool']['must'].append({"match_phrase": {"host": host_to_search}})
    # query_search['query']['filtered']['query']['bool']['must'].append({"match": {field1: value1}})

    res = es.search(size=docs, index=index, fields="@timestamp,message,path,host",
                    sort="@timestamp:asc",
                    body=query_search
                    )

    if len(res['hits']['hits']) != 0:
        timestamp = res['hits']['hits'][0]['sort'][0]
        to_object(res)
        single_run_purge_event_pool(event_pool)
    return

def search_events(from_date_time):
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-range-query.html
    # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.search

    query_search['query']['filtered']['filter']['range'] = {"@timestamp": {"gte": from_date_time}}

    res = es.search(size="10000", index=index, fields="@timestamp,message,path,host",
                        sort="@timestamp:asc", body=query_search)

def wait(milliseconds):
    # Current time in Epoch milliseconds
    current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])
    final_time = current_time + milliseconds
    len_print_pool = len(print_pool)

    if len_print_pool == 0:
        print('wibble... was this debug?')
        exit(0)

    while final_time > current_time:
        current_time = int(datetime.datetime.utcnow().strftime('%s%f')[:-3])
        what_to_do_while_we_wait()
        # Sleep just a bit to avoid hammering the CPU (to improve)
        time2.sleep(.01)


def what_to_do_while_we_wait():
    global print_pool
    len_print_pool_2 = len( print_pool )
    wait_interval = interval + .0

    for i in range(0,len_print_pool_2 ):
        sys.stdout.write( print_pool[i] )
        sys.stdout.flush()

        time2.sleep( (interval / len_print_pool_2 + .0) / wait_interval )

    print_pool = []


# Get lastest available index
def check_index():

    # Get indices list
    indices = []
    list = es.indices.get_alias("*")
    for index in list:
        # TODO make this a config option
        if index[0:9] == 'filebeat-':
            indices.append(str(index))
    if indices == []:
        sys.exit(1)
    indices = sorted(indices, reverse=True)
    return indices[0]


def thread_execution(from_date_time):

    if DUMMY:
        res = search_events_dummy_load(from_date_time)
    else:
        res = search_events(from_date_time)

    # Add all the events in the response into the event_pool
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

interval = 1000  # milliseconds

## { "_id": {"timestamp":"sort(in milliseconds)", "host":"", "type":"", "message":"") }
event_pool = {}

print_pool = []

to_the_past = 10000  # milliseconds

# Mutable query object base for main search
query_search = {
    "query": {
        "filtered": {
            "query": {
                "bool": {
                    "must": []
                }
            },
            "filter": {
                "range": {}
            }
        }
    }
}
# and for non continuous search (datetime filter not necessary)
query_latest = {
    "query": {
        "filtered": {
            "query": {
                "bool": {
                    "must": []
                }
            }
        }
    }
}


### Args
# --endpoint
if args.endpoint == 'dummy' or args.endpoint == 'DUMMY':
    DUMMY = True
    print ("INFO: Activating Dummy Load")
else:
    DUMMY = False
    endpoint = normalize_endpoint(args.endpoint)
# --host
if args.hostname:
    host_to_search = args.hostname
    query_search['query']['filtered']['query']['bool']['must'].append({"match_phrase": {"host": host_to_search}})
    query_latest['query']['filtered']['query']['bool']['must'].append({"match_phrase": {"host": host_to_search}})
else:
    host_to_search = ''
# --showheaders. Show @timestamp, hostname and type columns from the output.
if args.showheaders:
    show_headers = True
else:
    show_headers = False
# -f --nonstop
if args.nonstop:
    non_stop = True
else:
    non_stop = False
# -n --docs
docs = int(args.docs)
if docs < 1 or docs > 10000:
    print ("ERROR: Document range has to be between 1 and 10000")
    sys.exit(1)
# --level
if args.javalevel:
    value1 = args.javalevel
    query_search['query']['filtered']['query']['bool']['must'].append({"match": {"level": value1}})
    query_latest['query']['filtered']['query']['bool']['must'].append({"match": {"level": value1}})
# --javaclass
elif args.javaclass:
    value1 = args.javaclass
    query_search['query']['filtered']['query']['bool']['must'].append({"match": {"class": value1}})
    query_latest['query']['filtered']['query']['bool']['must'].append({"match": {"class": value1}})
# --httpresponse
elif args.httpresponse:
    value1 = args.httpresponse
    query_search['query']['filtered']['query']['bool']['must'].append({"match": {"server_response": value1}})
    query_latest['query']['filtered']['query']['bool']['must'].append({"match": {"server_response": value1}})
# --method
elif args.httpmethod:
    value1 = args.httpmethod
    query_search['query']['filtered']['query']['bool']['must'].append({"match": {"method": value1}})
    query_latest['query']['filtered']['query']['bool']['must'].append({"match": {"method": value1}})
else:
    value1 = ''

# http://elasticsearch-py.readthedocs.io/en/master/
ssl_context = create_ssl_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
es = Elasticsearch([endpoint],verify_certs=False,ssl_context=ssl_context,http_auth=("admin","admin"))

if not args.index:
  index = check_index()
else:
  index = args.index

# When not under -f just get the latest and exit
if non_stop == False:
    get_latest_events(index)
    sys.exit(0)

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

    # And here we go again...
