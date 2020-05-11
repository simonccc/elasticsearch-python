elastic = {'es_host': 'https://localhost:9200',
	 'user': 'admin',
	 'pass': 'admin'}
myindex = {'name': 'logstash'}
tail = {
        'sleep': '0.5',
        'buffer': '0.1',
        'result_size': '1000',
}
tail_colors = {
        'enabled': 'true',
        'red': '\x1b[1;33;91m',
        'blue': '\x1b[1;33;94m',
        'yellow': '\x1b[1;33;33m',
        'green': '\x1b[1;33;92m',
}
