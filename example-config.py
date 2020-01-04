elastic = {'es_host': 'https://localhost:9200',
	 'user': 'admin',
	 'pass': 'admin'}
#logstash and filebeat tested
myindex = {'name': 'logstash'}
tail = {
        'sleep': 0.2
}
tail_colors = {
        'enabled': 'true',
        'red': '\x1b[1;33;91m'
}
