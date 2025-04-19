import time
import redis
import os
import json
import requests
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, generate_random_64bit_string
import time
import random

def log_message(message):
    time_delay = random.randrange(0, 2000)
    print(f'[log_message] Waiting {time_delay}ms before logging message...')
    time.sleep(time_delay / 1000)
    print('[log_message] Message received:', message)

print('[main] Starting log-message-processor...')

redis_host = os.environ['REDIS_HOST']
redis_port = int(os.environ['REDIS_PORT'])
redis_password = os.environ['REDIS_PASSWORD'] if 'REDIS_PASSWORD' in os.environ else ''
redis_channel = os.environ['REDIS_CHANNEL']
zipkin_url = os.environ['ZIPKIN_URL'] if 'ZIPKIN_URL' in os.environ else ''

print(f'[main] Connecting to Redis at {redis_host}:{redis_port}')
print(f'[main] Subscribing to channel: {redis_channel}')
if zipkin_url:
    print(f'[main] Zipkin URL is set to: {zipkin_url}')
else:
    print('[main] Zipkin URL is not set')

def http_transport(encoded_span):
    print('[http_transport] Sending span to Zipkin...')
    response = requests.post(
        zipkin_url,
        data=encoded_span,
        headers={'Content-Type': 'application/x-thrift'},
    )
    print(f'[http_transport] Zipkin response status: {response.status_code}')

pubsub = redis.Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    decode_responses=True,
    db=0
).pubsub()
pubsub.subscribe([redis_channel])

print('[main] Listening for messages...')
for item in pubsub.listen():
    print('[main] Received raw item:', item)
    if item['type'] != 'message':
        continue

    try:
        message = json.loads(item['data'])
        print('[main] Parsed message:', message)
    except Exception as e:
        print('[main] Error parsing message:', e)
        log_message(item['data'])
        continue

    if not zipkin_url or 'zipkinSpan' not in message:
        print('[main] No Zipkin span found or Zipkin not configured.')
        log_message(message)
        continue

    span_data = message['zipkinSpan']
    print('[main] Starting Zipkin span with data:', span_data)
    try:
        with zipkin_span(
            service_name='log-message-processor',
            zipkin_attrs=ZipkinAttrs(
                trace_id=span_data['_traceId']['value'],
                span_id=generate_random_64bit_string(),
                parent_span_id=span_data['_spanId'],
                is_sampled=span_data['_sampled']['value'],
                flags=None
            ),
            span_name='save_log',
            transport_handler=http_transport,
            sample_rate=100
        ):
            log_message(message)
    except Exception as e:
        print('[main] Error sending data to Zipkin:', e)
        log_message(message)
