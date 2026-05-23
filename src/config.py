import os
from dotenv import load_dotenv


# Load variables from .env file
load_dotenv()


SERPER_API_KEY = os.getenv("SERPER_API_KEY") #or st.secrets.get("SERPER_API_KEY")


DEFAULT_NUM_RESULTS = 10


MIN_CONTENT_LENGTH = 200


PLAYWRIGHT_TIMEOUT = 30000
PLAYWRIGHT_WAIT_TIME = 5000


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


BLOCKED_DOMAINS = [
    "linkedin.com",
    "x.com",
    "twitter.com",
    "instagram.com",
    "facebook.com",
]