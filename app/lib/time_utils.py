"""Timezone utilities for Eastern Time handling"""
from datetime import datetime
import pytz

EASTERN_TZ = pytz.timezone("America/New_York")


def get_current_eastern_time() -> datetime:
    """Get current time in Eastern Time zone"""
    return datetime.now(EASTERN_TZ)


def format_eastern_time(dt: datetime) -> str:
    """Format datetime in Eastern Time zone as readable string"""
    if dt.tzinfo is None:
        dt = EASTERN_TZ.localize(dt)
    elif dt.tzinfo != EASTERN_TZ:
        dt = dt.astimezone(EASTERN_TZ)
    return dt.strftime("%A, %B %d, %Y at %I:%M %p Eastern Time")


def convert_utc_to_eastern(utc_iso_str: str) -> str:
    """Convert UTC ISO string from Cal.com API to Eastern Time string"""
    try:
        # Parse UTC ISO format (e.g., "2026-06-15T18:00:00.000Z")
        if utc_iso_str.endswith('Z'):
            utc_iso_str = utc_iso_str[:-1] + '+00:00'
        elif '+' not in utc_iso_str and utc_iso_str.count('-') >= 3:
            # Handle format like "2026-06-15T18:00:00.000"
            utc_iso_str = utc_iso_str + '+00:00'
        
        dt_utc = datetime.fromisoformat(utc_iso_str.replace('Z', '+00:00'))
        if dt_utc.tzinfo is None:
            dt_utc = pytz.UTC.localize(dt_utc)
        else:
            dt_utc = dt_utc.astimezone(pytz.UTC)
        
        # Convert to Eastern Time
        dt_eastern = dt_utc.astimezone(EASTERN_TZ)
        return format_eastern_time(dt_eastern)
    except Exception as e:
        import logging
        logger = logging.getLogger("agent-Alex-2f2")
        logger.error(f"Error converting UTC to Eastern: {e}, input: {utc_iso_str}")
        # Fallback: return the original string
        return utc_iso_str


def convert_to_utc_iso(eastern_time_str: str) -> str:
    """Convert Eastern Time string to UTC ISO format for Cal.com API"""
    import logging
    logger = logging.getLogger("agent-Alex-2f2")
    
    try:
        time_str = eastern_time_str.strip()
        formats = [
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %I:%M:%S %p", "%B %d, %Y %I:%M %p",
            "%B %d, %Y %I:%M:%S %p", "%b %d, %Y %I:%M %p",
            "%b %d, %Y %I:%M:%S %p", "%Y-%m-%d %I:%M %p",
            "%Y-%m-%d %I:%M:%S %p",
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        
        if dt is None:
            raise ValueError(f"Could not parse time string: {eastern_time_str}")
        
        if dt.tzinfo is None:
            dt = EASTERN_TZ.localize(dt)
        elif dt.tzinfo != EASTERN_TZ:
            dt = dt.astimezone(EASTERN_TZ)
        
        dt_utc = dt.astimezone(pytz.UTC)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        logger.error(f"Error converting time to UTC: {e}")
        raise

