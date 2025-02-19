import os
import time
import datetime
import subprocess
import psutil
from jinja2 import Environment, FileSystemLoader

from src.logger import logger
from src.models import GeneralSettings
from src.helper import get_system_node_name, get_ip_address

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Simple in-memory cache for specific data with individual timestamps
cache = {}
# enable_cahce = True # moved to the database
CACHE_EXPIRATION = 3600
DIVIDE_BY_1024 = False
CONVERSION_FACTOR_MB = (1024 ** 2) if DIVIDE_BY_1024 else (1000 ** 2)
CONVERSION_FACTOR_GB = (1024 ** 3) if DIVIDE_BY_1024 else (1000 ** 3)


def format_uptime(uptime_seconds):
    """Convert uptime from seconds to a human-readable format.
    ---
    Parameters:
        uptime_seconds (datetime.timedelta): Uptime in seconds.
    ---
    Returns:
        dict: Uptime in days, hours, minutes, and seconds.

    """
    uptime_seconds = uptime_seconds.total_seconds()
    days = int(uptime_seconds // (24 * 3600))
    uptime_seconds %= (24 * 3600)
    hours = int(uptime_seconds // 3600)
    uptime_seconds %= 3600
    minutes = int(uptime_seconds // 60)
    seconds = int(uptime_seconds % 60)
    
    return {
        'uptime_days': days,
        'uptime_hours': hours,
        'uptime_minutes': minutes,
        'uptime_seconds': seconds
    }


def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object to a string.
    ---
    Parameters:
        value (datetime.datetime): Datetime object to format.
        format (str): Format string for the output.
    ---
    Returns:
        str: Formatted datetime string.
    """
    return value.strftime(format)

def get_flask_memory_usage():
    """
    Returns the memory usage of the current Flask application in MB.
    ---
    Parameters:
        None
    ---
    Returns:
        float: Memory usage of the Flask application in MB.
    """
    try:
        pid = os.getpid()  # Get the current process ID
        process = psutil.Process(pid)  # Get the process information using psutil
        memory_info = process.memory_info()  # Get the memory usage information
        memory_in_mb = memory_info.rss / CONVERSION_FACTOR_MB
        return round(memory_in_mb)  # Return the memory usage rounded to 2 decimal places
    except Exception as e:
        logger.info(f"Error getting memory usage: {e}")
        return None
    
def get_established_connections():
    """ 
    Get the first available IPv4 and IPv6 addresses of established network connections.
    ---
    Parameters:
        None
    ---
    Returns:
        tuple: First available IPv4 and IPv6 addresses of established network connections.
    """
    # Get all active network connections of type 'inet' (IPv4 and IPv6)
    connections = psutil.net_connections(kind='inet')
    
    # Use sets to store unique IPv4 and IPv6 addresses
    ipv4_addresses = set()
    ipv6_addresses = set()

    # Iterate through each connection
    for conn in connections:
        # Filter only established connections
        if conn.status == 'ESTABLISHED':
            # Check if the local address (laddr) is IPv4 or IPv6 and add to the corresponding set
            if '.' in conn.laddr.ip:
                ipv4_addresses.add(conn.laddr.ip)
            elif ':' in conn.laddr.ip:
                ipv6_addresses.add(conn.laddr.ip)

    # Return the first available IP from each set, or "N/A" if none found
    ipv4 = next(iter(ipv4_addresses), "N/A")
    ipv6 = next(iter(ipv6_addresses), "N/A")

    return ipv4, ipv6

def run_speedtest():
    """ Run a speed test using speedtest-cli.
    ---
    Parameters:
        None
    ---
    Returns:
        dict: Download speed, upload speed, ping, and status of the speed test.
    """
    try:
        result = subprocess.run(['speedtest-cli'], capture_output=True, text=True, check=True)
        output_lines = result.stdout.splitlines()
        download_speed, upload_speed, ping = None, None, None

        for line in output_lines:
            if "Download:" in line:
                download_speed = line.split("Download: ")[1]
            elif "Upload:" in line:
                upload_speed = line.split("Upload: ")[1]
            elif "Ping:" in line:
                ping = line.split("Ping: ")[1]

        return {"download_speed": download_speed, "upload_speed": upload_speed, "ping": ping, "status": "Success"}

    except subprocess.CalledProcessError as e:
        return {"status": "Error", "message": e.stderr}

    except Exception as e:
        return {"status": "Error", "message": str(e)}

def get_cpu_frequency():
    """
    Get the current CPU frequency in MHz.
    ---
    Parameters:
        None
    ---
    Returns:
        int: Current CPU frequency in MHz.
    """
    return round(psutil.cpu_freq().current)

def get_cpu_core_count():
    """
    Get the number of CPU cores.
    ---
    Parameters:
    ---
    Returns:
        int: Number of CPU cores.
    """
    return psutil.cpu_count(logical=True)

def cpu_usage_percent():
    """
    Get the current CPU usage percentage.
    ---
    Parameters:
    ---
    Returns:
        float: Current CPU usage percentage
    """
    return psutil.cpu_percent(interval=1)

def get_cpu_temp():
    """
    Get the current CPU temperature, high temperature, and critical temperature.

    Returns:
        tuple: Current CPU temperature, high temperature, and critical temperature.
    """
    try:
        # Fetch temperatures for sensors labeled 'coretemp'
        temps = psutil.sensors_temperatures().get('coretemp')
        
        # Check if we have temperatures data
        if temps:
            temp = temps[0]  # Get the first sensor's readings
            
            # Extract current, high, and critical temperatures
            current_temp = getattr(temp, 'current', 'N/A')
            high_temp = getattr(temp, 'high', 'N/A')
            critical_temp = getattr(temp, 'critical', 'N/A')
            
            return (current_temp, high_temp, critical_temp)
        else:
            # If no 'coretemp' sensors found, return 'N/A'
            return ("N/A", "N/A", "N/A")
    
    except Exception as e:
        logger.warning(f"Error getting CPU temperature: {e}")
        return ("N/A", "N/A", "N/A")


def get_top_processes(number=5):
    """Get the top processes by memory usage.
    ---
    Parameters:
        number (int): Number of top processes to return.
    ---
    Returns:
        list: List of top processes with name, CPU percent, memory percent, and PID.
    """
    processes = [
        (p.info['name'], p.info['cpu_percent'], round(p.info['memory_percent'], 2), p.info['pid'])
        for p in sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid']),
                        key=lambda p: p.info['memory_percent'], reverse=True)[:number]
    ]
    return processes

def get_disk_free():
    """Returns the free disk space in GB.
    ---
    Parameters:
    ---
    Returns:
        float: Free disk space in GB
    """
    return round(psutil.disk_usage("/").free / CONVERSION_FACTOR_GB, 1)

def get_disk_used():
    """Returns the used disk space in GB.
    ---
    Parameters:
    ---
    Returns:
        float: Used disk space in GB
    """
    return round(psutil.disk_usage("/").used / CONVERSION_FACTOR_GB, 1)

def get_disk_total():
    """Returns the total disk space in GB.
    ---
    Parameters:
    ---
    Returns:
        float: Total disk space in GB
    """
    return round(psutil.disk_usage("/").total / CONVERSION_FACTOR_GB, 1)

def get_disk_usage_percent():
    """Returns the percentage of disk used.
    ---
    Parameters:
    ---
    Returns:
        tuple: Disk usage percentage and calculated disk usage percentage
    """
    disk_usage = psutil.disk_usage("/")
    calculated_percent = (disk_usage.used / disk_usage.total) * 100
    return disk_usage.percent, round(calculated_percent, 1)


def get_memory_available():
    """Returns the available memory in GB.
    ---
    Parameters:
    ---
    Returns:
        float: Available memory in GB
    """
    return round(psutil.virtual_memory().total / CONVERSION_FACTOR_GB, 1)


def get_memory_used():
    """Returns the used memory in GB.
    ---
    Parameters:
    ---
    Returns:
        float: Used memory in GB
    """
    return round((psutil.virtual_memory().total - psutil.virtual_memory().available) / CONVERSION_FACTOR_GB, 2)

def get_memory_percent():
    """Returns the percentage of memory used.
    ---
    Parameters:
    ---
    Returns:
        float: Memory usage percentage
    """
    return psutil.virtual_memory().percent

def get_swap_memory_info():
    """Returns the total, used, and free swap memory in GB.
    ---
    Parameters:
    --- 
    Returns:
        dict: Total, used, and free swap memory in GB
    """
    swap = psutil.swap_memory()
    total_swap = swap.total
    used_swap = swap.used
    free_swap = total_swap - used_swap  # Calculate free swap memory

    return {
        "total_swap": round(total_swap / CONVERSION_FACTOR_GB, 1),  # In GB
        "used_swap": round(used_swap / CONVERSION_FACTOR_GB, 1),    # In GB
        "free_swap": round(free_swap / CONVERSION_FACTOR_GB, 1)     # In GB
    }

def render_template_from_file(template_file_path, **context):
    """
    Renders a Jinja template from a file with the given context and returns the rendered HTML content.

    :param template_file_path: Path to the template file to render.
    :param context: Context variables to pass to the template.
    :return: Rendered HTML content as a string.
    """
    template_dir = os.path.dirname(template_file_path)
    template_file = os.path.basename(template_file_path)
    
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Load the template file
    template = env.get_template(template_file)
    
    # Render the template with the provided context
    rendered_html = template.render(**context)
    
    return rendered_html

def get_cached_value(key, fresh_value_func):
    """ Get a cached value if available and not expired, otherwise get fresh value. 
    ---
    Parameters:
        key (str): Key to store the value in the cache.
        fresh_value_func (function): Function to get the fresh value if the cache is expired.
    ---
    Returns:
        Any: Cached value if available and not expired, otherwise the fresh value.
    """
    general_settings = GeneralSettings.query.first()
    if general_settings:
        enable_cahce = general_settings.enable_cache
    
    current_time = time.time()
    # if key not in cache, create a new entry
    if key not in cache:
        cache[key] = {'value': None, 'timestamp': 0}

    # Check if cache is valid
    if enable_cahce and cache[key]['value'] is not None and (current_time - cache[key]['timestamp'] < CACHE_EXPIRATION):
        return cache[key]['value']

    # Fetch fresh value
    fresh_value = fresh_value_func()

    # Store value in cache
    cache[key]['value'] = fresh_value
    cache[key]['timestamp'] = current_time

    return fresh_value


def _get_system_info():
    """ Get system information with caching for certain values and fresh data for others. 
    ---
    Parameters:
    ---
    Returns:
        dict: System information dictionary with various system metrics.
    """
    boot_time = get_cached_value('boot_time', lambda: datetime.datetime.fromtimestamp(psutil.boot_time()))
    uptime_dict = get_cached_value('uptime', lambda: format_uptime(datetime.datetime.now() - boot_time))

    # Gathering fresh system information
    battery_info = psutil.sensors_battery()
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    net_io = psutil.net_io_counters(pernic=False)
    network_sent = round(net_io.bytes_sent / CONVERSION_FACTOR_MB, 1)  # In MB
    network_received = round(net_io.bytes_recv / CONVERSION_FACTOR_MB, 1)  # In MB
    # ifconfig | grep -E 'RX packets|TX packets' -A 1

    # Prepare system information dictionary
    info = {
        'cpu_percent': cpu_usage_percent(),
        'memory_percent': round(memory_info.percent, 2),
        'disk_percent': round(disk_info.percent, 2),
        'network_sent': network_sent,
        'battery_percent': round(battery_info.percent, 1) if battery_info else "N/A",
        'network_received': network_received,
        "network_stats" : f"D: {network_received} MB / U: {network_sent} MB",
        'dashboard_memory_usage': get_flask_memory_usage(),
        'cpu_frequency': get_cpu_frequency(),
        'current_temp': get_cpu_temp()[0],
        'timestamp': datetime.datetime.now(),
    }
    # update uptime dictionary
    info.update(uptime_dict)

    return info

def get_system_info():
    """ Get system information with caching for certain values and fresh data for others. 
    ---
    Parameters:
    ---
    Returns:
        dict: System information dictionary with various system metrics.
    """
    username = get_cached_value('username', get_system_node_name)
    ipv4_address = get_cached_value('ipv4', lambda: get_ip_address())
    boot_time = get_cached_value('boot_time', lambda: datetime.datetime.fromtimestamp(psutil.boot_time()))
    uptime_dict = get_cached_value('uptime', lambda: format_uptime(datetime.datetime.now() - boot_time))
    current_server_time = datetime.datetime.now()

    # Prepare system information dictionary
    info = {
        'username': username,
        'cpu_core': get_cpu_core_count(),
        'boot_time': boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        'process_count': len(psutil.pids()),
        'swap_memory': psutil.swap_memory().percent,
        'ipv4_connections': ipv4_address,
        'timestamp': datetime.datetime.now(),
        'current_server_time': current_server_time.strftime("%Y-%m-%d %H:%M:%S"),
        'timestamp': current_server_time
    }
    # update uptime dictionary
    _info = _get_system_info()
    info.update(uptime_dict)
    info.update(_info)

    return info
