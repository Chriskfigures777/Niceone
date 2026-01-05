"""Cal.com API v2 client"""
import logging
import ssl
import certifi
import os
from typing import Optional, Dict, Any, List
import httpx
from httpx import HTTPStatusError

logger = logging.getLogger("agent-Alex-2f2")

# Configure SSL certificates for macOS compatibility
cert_path = certifi.where()
os.environ.setdefault("SSL_CERT_FILE", cert_path)
os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)
ssl_context = ssl.create_default_context(cafile=cert_path)

CALCOM_API_BASE = "https://api.cal.com/v2"
CALCOM_API_VERSION = "2024-08-13"
CONNECT_MEETING_EVENT_TYPE_ID = 4145759
DISCOVER_MEETING_EVENT_TYPE_ID = 4145757


class CalComClient:
    """Client for Cal.com API v2"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = CALCOM_API_BASE
        self.api_version = CALCOM_API_VERSION
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "cal-api-version": self.api_version,
            "Content-Type": "application/json",
        }
    
    async def get_all_bookings(self, take: int = 100, status: Optional[str] = "upcoming", email: Optional[str] = None) -> Dict[str, Any]:
        """Get all bookings, optionally filtered by email"""
        try:
            params = {"take": take}
            if status:
                params["status"] = status
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.get(f"{self.base_url}/bookings", headers=self.headers, params=params, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                # Cal.com API v2 returns: {"status": "success", "data": [...], "pagination": {...}}
                # Extract bookings from 'data' field
                bookings = result.get('data', [])
                
                # Filter by email if provided (case-insensitive, check both attendees and bookingFieldsResponses)
                if email:
                    email_lower = email.lower()
                    filtered_bookings = []
                    for booking in bookings:
                        # Check attendees email
                        attendee_emails = [a.get('email', '').lower() for a in booking.get('attendees', [])]
                        # Check bookingFieldsResponses email
                        booking_email = booking.get('bookingFieldsResponses', {}).get('email', '').lower()
                        # Check hosts email (sometimes user books for themselves)
                        host_emails = [h.get('email', '').lower() for h in booking.get('hosts', [])]
                        
                        # Match if email appears in any of these locations
                        if (email_lower in attendee_emails or 
                            email_lower == booking_email or 
                            email_lower in host_emails):
                            filtered_bookings.append(booking)
                    
                    bookings = filtered_bookings
                
                # Filter out cancelled bookings when status is "upcoming" (API should do this, but double-check)
                if status == "upcoming":
                    bookings = [b for b in bookings if b.get('status', '').lower() != 'cancelled']
                
                # Return in expected format
                return {
                    'bookings': bookings,
                    'total': len(bookings),
                    'pagination': result.get('pagination', {})
                }
        except Exception as e:
            logger.error(f"Error getting bookings: {e}")
            raise
    
    async def get_booking(self, booking_uid: str) -> Dict[str, Any]:
        """Get a specific booking by UID"""
        try:
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.get(f"{self.base_url}/bookings/{booking_uid}", headers=self.headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                # Cal.com API v2 returns {"status": "success", "data": {...}}
                return result.get('data', result) if isinstance(result, dict) and 'data' in result else result
        except HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body}"
            except:
                error_detail = f" - Status: {e.response.status_code}"
            logger.error(f"Error getting booking {booking_uid}: {e.response.status_code}{error_detail}")
            raise Exception(f"Cal.com API error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            logger.error(f"Error getting booking {booking_uid}: {e}")
            raise
    
    async def create_booking(self, event_type_id: int, start_time: str, attendee_name: str, attendee_email: str, attendee_timezone: str = "America/New_York", language: str = "en", notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a new booking. Optionally include notes/description."""
        try:
            data = {
                "eventTypeId": event_type_id,
                "start": start_time,
                "attendee": {"name": attendee_name, "email": attendee_email, "timeZone": attendee_timezone, "language": language},
            }
            # Add notes if provided (Cal.com API v2 supports notes field)
            if notes:
                data["notes"] = notes
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.post(f"{self.base_url}/bookings", headers=self.headers, json=data, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                # Cal.com API v2 returns {"status": "success", "data": {...}}
                return result.get('data', result) if isinstance(result, dict) and 'data' in result else result
        except HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body}"
            except:
                error_detail = f" - Status: {e.response.status_code}"
            logger.error(f"Error creating booking: {e.response.status_code}{error_detail}")
            raise Exception(f"Cal.com API error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            raise
    
    async def reschedule_booking(self, booking_uid: str, new_start_time: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reschedule a booking - creates a new booking and links to the old one"""
        try:
            data = {"start": new_start_time}
            if reason:
                data["reschedulingReason"] = reason
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.post(f"{self.base_url}/bookings/{booking_uid}/reschedule", headers=self.headers, json=data, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                # Cal.com API v2 returns {"status": "success", "data": {...}} with new booking
                # The new booking has "rescheduledFromUid" linking to the old booking
                return result.get('data', result) if isinstance(result, dict) and 'data' in result else result
        except HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body}"
            except:
                error_detail = f" - Status: {e.response.status_code}"
            logger.error(f"Error rescheduling booking {booking_uid}: {e.response.status_code}{error_detail}")
            raise Exception(f"Cal.com API error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            logger.error(f"Error rescheduling booking {booking_uid}: {e}")
            raise
    
    async def cancel_booking(self, booking_uid: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a booking"""
        try:
            data = {}
            if reason:
                data["cancellationReason"] = reason
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.post(f"{self.base_url}/bookings/{booking_uid}/cancel", headers=self.headers, json=data, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                # Cal.com API v2 returns {"status": "success", "data": {...}} with updated booking (status: "cancelled")
                return result.get('data', result) if isinstance(result, dict) and 'data' in result else result
        except HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body}"
            except:
                error_detail = f" - Status: {e.response.status_code}"
            logger.error(f"Error canceling booking {booking_uid}: {e.response.status_code}{error_detail}")
            raise Exception(f"Cal.com API error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            logger.error(f"Error canceling booking {booking_uid}: {e}")
            raise
    
    async def add_guests(self, booking_uid: str, guests: List[Dict[str, str]]) -> Dict[str, Any]:
        """Add guests to a booking"""
        try:
            data = {"guests": guests}
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.post(f"{self.base_url}/bookings/{booking_uid}/guests", headers=self.headers, json=data, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                # Cal.com API v2 returns {"status": "success", "data": {...}} with updated booking
                return result.get('data', result) if isinstance(result, dict) and 'data' in result else result
        except HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body}"
            except:
                error_detail = f" - Status: {e.response.status_code}"
            logger.error(f"Error adding guests to booking {booking_uid}: {e.response.status_code}{error_detail}")
            raise Exception(f"Cal.com API error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            logger.error(f"Error adding guests to booking {booking_uid}: {e}")
            raise

