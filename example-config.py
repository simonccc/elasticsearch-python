elastic = {'es_host': 'https://localhost:9200',
	 'user': 'admin',
	 'pass': 'admin'}
#logstash and filebeat tested
myindex = {'name': 'logstash'}
#  how long to sleep between requests in seconds
tail = {
        'sleep': 0.5
        'result_size': 1000
}
tail_colors = {
        'enabled': 'true',
        'red': '\x1b[1;33;91m',
        'blue': '\x1b[1;33;94m',
        'yellow': '\x1b[1;33;33m',
        'green': '\x1b[1;33;92m',
}
