import bandwidth_cache
import datetime
import re


def convert_str_to_datetime(date_str):
    return datetime.datetime.strptime(date_str, '%d/%b/%Y:%H:%M:%S')


def line_parser(str_line):
    pattern = "(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) - - \[" \
              "(?P<date>\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2})?\] \"" \
              "(?P<http_request>\w+)? /\w+/\w+/" \
              "(?P<id>\w+)?/(?P<type>\w+)?"
    pattern_2 = ".*?(\d+)$"
    results = re.match(pattern, str_line)
    if results is not None:
        results = re.match(pattern, str_line).groupdict()
    else:
        return results
    temp_results = re.match(pattern_2, str_line)
    if temp_results is not None:
        results['size'] = re.match(pattern_2, str_line).group(1)
    else:
        results['size'] = None
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


@bandwidth_cache.put(time=60 * 60 * 24)  # Key expires in 24hs
def store_data(key, content):
    return content


def generate_bandwidth_data():
    parsed_data = []
    end_times = {}
    for line in reversed(open("/var/log/supervisor/access.log").readlines()):
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
                        timedelta(days=3)
                    if end_time > min_time:
                        store_data(str_start_time + ':' + str_end_time,
                                   bandwidth)
                end_times.pop(key, None)

generate_bandwidth_data()
