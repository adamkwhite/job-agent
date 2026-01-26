"""URL validation utilities for job links"""

import logging

import requests

logger = logging.getLogger(__name__)


def validate_job_url(url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Validate job URL is accessible

    Args:
        url: Job URL to validate
        timeout: Request timeout in seconds

    Returns:
        (is_valid, reason): Tuple of validation result and reason
    """
    try:
        # Use HEAD request (faster than GET)
        response = requests.head(url, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            return (True, "valid")
        elif response.status_code == 404:
            return (False, "not_found")
        elif 500 <= response.status_code < 600:
            # Server error - might be transient, retry once
            logger.warning(f"Server error for {url}, retrying...")
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return (True, "valid_after_retry")
            return (False, f"server_error_{response.status_code}")
        else:
            return (False, f"http_{response.status_code}")

    except requests.Timeout:
        logger.warning(f"Timeout validating URL: {url}")
        return (False, "timeout")
    except requests.ConnectionError:
        logger.warning(f"Connection error validating URL: {url}")
        return (False, "connection_error")
    except Exception as e:
        logger.error(f"Unexpected error validating URL: {url} - {e}")
        return (False, f"error: {str(e)[:50]}")
