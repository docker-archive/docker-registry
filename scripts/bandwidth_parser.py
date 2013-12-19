import datetime
import json
import logging
import os
import re
import redis
import sys

cfg_path = os.path.realpath('config')
sys.path.append(cfg_path)

import gunicorn_config

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('metrics')

redis_opts = {}
redis_conn = None
cache_prefix = 'bandwidth_log:'
logging_period = 60 * 24  # 24hs
logging_interval = 15  # 15 minutes
exp_time = 60 * 60 * 24  # Key expires in 24hs
try:
    with open('/home/dotcloud/environment.json') as f:
        env = json.load(f)
        # Prod
        redis_opts = {
            'host': env['DOTCLOUD_REDIS_REDIS_HOST'],
            'port': int(env['DOTCLOUD_REDIS_REDIS_PORT']),
            'db': 1,
            'password': env['DOTCLOUD_REDIS_REDIS_PASSWORD'],
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


def raw_line_parser(str_line):
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


def set_cache(key, bandwidth):
    global redis_conn, cache_prefix, exp_period
    if redis_conn is None:
        logger.info('Failed to find a redis connection.')
        return
    redis_conn.setex(key, exp_time, bandwidth)  # time in seconds
    logger.info('Saved in Redis: key: {0} bandwidth: {1}'.format(key,
                                                                 bandwidth))


def adjust_current_interval(current_interval, end_time, items):
    global logging_interval, logging_period
    total_items = logging_period / logging_interval
    logger.info('Skipping interval: {0}'.format(current_interval))
    for i in range(items, total_items):
        items = i + 1
        current_interval -= datetime.timedelta(minutes=logging_interval)
        if current_interval <= end_time:
            break
        logger.info('Skipping interval: {0}'.format(current_interval))
    return current_interval, items


def save_bandwidth(bandwidth, key, items):
    # Save the average bandwidth of the give items
    avg_bandwidth = round(bandwidth[key] / items[key], 2)
    logger.info('Saving in Redis...')
    set_cache(key, avg_bandwidth)


def update_current_interval(items, logging_interval, start_time):
    items += 1
    interval = logging_interval * items
    current_interval = start_time - datetime.timedelta(minutes=interval)
    logger.info('Updating interval to: {0}'.format(current_interval))
    return current_interval, items


def parse_data(item):
    str_start_time = None
    str_end_time = None
    str_layer_size = None
    key = None
    if item['http_request'] is not None and item['type'] is not None:
            if 'GET' in item['http_request'] and 'layer' in item['type']:
                str_end_time = item['date']
            elif 'GET' in item['http_request'] and 'json' in item['type']:
                str_start_time = item['date']
                str_layer_size = item['size']
            key = item['id']
    return str_start_time, str_end_time, str_layer_size, key


def read_file():
    logger.info('Reading file...')
    parsed_data = []
    with open(gunicorn_config.accesslog) as f:
        for line in reversed(f.readlines()):
            processed_line = raw_line_parser(line.rstrip())
            if processed_line is not None:
                parsed_data.append(processed_line)
    return parsed_data


def generate_bandwidth_data(start_time, min_time, time_interval):
    global logging_interval, logging_period
    end_times = {}
    bandwidth_items = {}
    num_items = {}
    total_items = logging_period / logging_interval
    items = 1
    parsed_data = read_file()
    for item in parsed_data:
        str_start_time, str_end_time, str_layer_size, key = parse_data(item)
        if str_end_time:
            end_times[key] = str_end_time
        else:
            str_end_time = end_times.get(key)
        bandwidth = compute_bandwidth(str_end_time,
                                      str_start_time,
                                      str_layer_size)
        if bandwidth:
            end_time = convert_str_to_datetime(str_end_time)
            if end_time < min_time:
                break
            if items >= total_items:
                break
            if time_interval > end_time:
                if bandwidth_items.get(time_interval, 0):
                    save_bandwidth(bandwidth_items,
                                   time_interval,
                                   num_items)
                    time_interval, items = \
                        update_current_interval(items,
                                                logging_interval,
                                                start_time)
                else:
                    time_interval, items = \
                        adjust_current_interval(time_interval,
                                                end_time,
                                                items)
            bandwidth_items[time_interval] = \
                bandwidth_items.get(time_interval, 0.0) \
                + bandwidth
            num_items[time_interval] = \
                num_items.get(time_interval, 0.0) + 1
            end_times.pop(key, None)


def run():
    global redis_conn, redis_opts
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    logger.info('Redis config: {0}'.format(redis_opts))
    start_time = datetime.datetime.utcnow()
    min_time = start_time - datetime.timedelta(minutes=logging_period)
    time_interval = start_time - datetime.timedelta(minutes=logging_interval)
    logger.info('Starting...')
    generate_bandwidth_data(start_time, min_time, time_interval)

if __name__ == "__main__":
    run()
