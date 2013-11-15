import datetime
import json
import os
import re
import redis
import sys

cfg_path = os.path.realpath('')
sys.path.append(cfg_path)

import gunicorn_config

redis_opts = {}
redis_conn = None
cache_prefix = 'bandwidth_log:'
exp_time = 60 * 60 * 24  # Key expires in 24hs
try:
    with open('/home/dotcloud/environment.json') as f:
        env = json.load(f)
        # Prod
        redis_opts = {
            'host': env['DOTCLOUD_BANDWIDTH_REDIS_HOST'],
            'port': int(env['DOTCLOUD_BANDWIDTH_REDIS_PORT']),
            'db': 0,
            'password': env['DOTCLOUD_BANDWIDTH_REDIS_PASSWORD'],
        }
except Exception:
    # Dev
    redis_opts = {
        'host': 'localhost',
        'port': 6380,
        'db': 0,
        'password': None,
    }


def convert_str_to_datetime(date_str):
    return datetime.datetime.strptime(date_str, '%d/%b/%Y:%H:%M:%S')


def line_parser(str_line):
    pattern = ("(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) - - \["
               "(?P<date>\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2})?\] \""
               "(?P<http_request>\w+)? /\w+/\w+/"
               "(?P<id>\w+)?/(?P<type>\w+)?")
    pattern_2 = ".*?(\d+)$"
    results = re.match(pattern, str_line)
    if results is None:
        return results
    results = re.match(pattern, str_line).groupdict()
    temp_results = re.match(pattern_2, str_line)
    if temp_results is None:
        results['size'] = None
        return results
    results['size'] = re.match(pattern_2, str_line).group(1)
    return results


def compute_bandwidth(str_end_time, str_start_time, str_layer_size):
    bandwidth = 0.0
    if str_start_time is None:
        return bandwidth
    if str_end_time is None:
        return bandwidth
    if str_layer_size is None:
        return bandwidth
    start_time = convert_str_to_datetime(str_start_time)
    end_time = convert_str_to_datetime(str_end_time)
    layer_size = long(str_layer_size)
    layer_size_mb = (layer_size * 8) / (1000 * 1000)  # Megabits
    delta = end_time - start_time
    num_seconds = delta.total_seconds()
    bandwidth = 0.0
    if num_seconds:
        bandwidth = layer_size_mb / num_seconds  # Megabits-per-second (Mbps)
    return bandwidth


def set_cache(str_start_time, str_end_time, bandwidth):
    global redis_conn, cache_prefix, exp_period
    key = cache_prefix + str_start_time + ':' + str_end_time
    if redis_conn is None:
        return
    redis_conn.setex(key, exp_time, bandwidth)  # time in seconds


def generate_bandwidth_data():
    global redis_conn, redis_opts
    parsed_data = []
    end_times = {}
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    with open(gunicorn_config.accesslog) as f:
        for line in reversed(f.readlines()):
            processed_line = line_parser(line.rstrip())
            if processed_line is not None:
                parsed_data.append(processed_line)
    for item in parsed_data:
        if item['http_request'] is not None and item['type'] is not None:
            if 'GET' in item['http_request'] and 'layer' in item['type']:
                key = item['ip'] + ':' + item['id']
                end_times[key] = item['date']
            elif 'GET' in item['http_request'] and 'json' in item['type']:
                key = item['ip'] + ':' + item['id']
                str_end_time = end_times.get(key)
                str_start_time = item['date']
                str_layer_size = item['size']
                bandwidth = round(compute_bandwidth(str_end_time,
                                                    str_start_time,
                                                    str_layer_size), 2)
                if bandwidth:
                    end_time = convert_str_to_datetime(str_end_time)
                    min_time = datetime.datetime.now() - datetime.\
                        timedelta(days=1)
                    if end_time > min_time:
                        set_cache(str_start_time, str_end_time, bandwidth)
                end_times.pop(key, None)

if __name__ == "__main__":
    generate_bandwidth_data()
