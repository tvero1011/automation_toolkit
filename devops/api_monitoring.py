import requests
import time

def check_endpoint(url, latency=5):
    try:
        start_time = time.time()
        response = requests.get(url)
        end_time = time.time()
        elapsed = end_time - start_time

        status_code = response.status_code

        if elapsed >= latency and status_code < 400:
            return "slow"

        if status_code >= 400:
            return "down"

        if elapsed < latency and status_code < 400:
            return "up"
    
    except Exception as e:
        print(f"Error checking endpoint {url}: {e}")
        return "down"

def check_all_endpoints():
    endpoints = ["/api/checkout", "/api/login", "/api/products", "/api/cart"]
    endpoint_status = {}
    for endpoint in endpoints:
        url = "https://example.com" + endpoint
        status = check_endpoint(url)
        if status == "down" or status == "slow":
            endpoint_status[endpoint] = status
    return endpoint_status