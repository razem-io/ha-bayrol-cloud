"""Constants for the Bayrol Pool API client."""

BASE_URL = "https://www.bayrol-poolaccess.de/webview"

# List of known compatible device models
COMPATIBLE_DEVICE_MODELS = [
    "Pool Relax Cl",
    "PoolManager Chlor (Cl)",
    "PoolManager PRO",
    "Automatic SALT",
]

# GitHub repository info for creating issues
GITHUB_ISSUES_URL = "https://github.com/razemio/ha-bayrol/issues/new"

# Common headers used in all requests
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept-Language": "en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Sec-Fetch-User": "?1",
}

# Login specific headers
LOGIN_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.bayrol-poolaccess.de",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

# Controllers list headers
CONTROLLERS_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

# Data fetch headers
DATA_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# JSON API headers
JSON_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=utf-8",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}
