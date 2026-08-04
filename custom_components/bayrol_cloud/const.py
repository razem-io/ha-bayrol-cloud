"""Constants for the Bayrol Pool Controller integration."""

DOMAIN = "bayrol_cloud"
CONF_CID = "cid"
CONF_SETTINGS_PASSWORD = "settings_password"
ISSUE_REPORT_URL = (
    "https://github.com/razem-io/ha-bayrol-cloud/issues/new"
    "?template=device-parser.yml"
    "&title=%5BBug%5D%3A+Device+status+parser+failed"
)

# Refresh interval settings
MIN_REFRESH_INTERVAL = 30  # minimum refresh interval in seconds
DEFAULT_REFRESH_INTERVAL = 300  # default refresh interval in seconds (5 minutes)
