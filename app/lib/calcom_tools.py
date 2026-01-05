"""Cal.com function tools for the agent"""
from typing import Optional, List
from datetime import datetime
import pytz
from livekit.agents import function_tool
from lib.calcom_client import CalComClient, CONNECT_MEETING_EVENT_TYPE_ID, DISCOVER_MEETING_EVENT_TYPE_ID
from lib.time_utils import get_current_eastern_time, format_eastern_time, convert_to_utc_iso, convert_utc_to_eastern

# Shared email state for tools (updated by agent)
_email_state = {"email": ""}

def create_calcom_tools(calcom_client: CalComClient, default_email: str, agent_instance=None):
    """Create and return Cal.com function tools. The agent_instance parameter allows tools to access conversation history for meeting notes."""
    
    @function_tool()
    async def get_all_bookings(take: int = 100, status: str = "upcoming", email: Optional[str] = None) -> str:
        """Get all bookings from Cal.com. Use status='upcoming' for future appointments, 'past' for past appointments, or 'cancelled' for cancelled ones. If email is provided, filters bookings for that email address. ALWAYS call this function when the user asks about their appointments - never make up or guess appointment data. If no email is provided, use the user's email from the conversation context."""
        try:
            # Get email from parameter, shared state, agent instance, or default
            filter_email = email
            if not filter_email:
                filter_email = _email_state.get("email")
            if not filter_email and agent_instance and hasattr(agent_instance, 'user_email'):
                filter_email = agent_instance.user_email
            if not filter_email:
                filter_email = default_email
            
            if not filter_email:
                return "Error: No email address provided. Please set your email in settings or provide it when asking about appointments."
            
            result = await calcom_client.get_all_bookings(take=take, status=status, email=filter_email)
            current_time = format_eastern_time(get_current_eastern_time())
            bookings = result.get('bookings', [])
            if not bookings:
                return f"Retrieved bookings at {current_time}. No bookings found for email {filter_email}."
            
            # Format booking details in a readable way (convert UTC to Eastern)
            booking_details = []
            for booking in bookings:
                # API returns 'start' field in UTC (e.g., "2026-06-15T18:00:00.000Z")
                start_time_utc = booking.get('start', booking.get('startTime', ''))
                # Convert UTC to Eastern Time for display
                if start_time_utc:
                    try:
                        start_time_eastern = convert_utc_to_eastern(start_time_utc)
                    except:
                        start_time_eastern = start_time_utc
                else:
                    start_time_eastern = 'Unknown time'
                
                title = booking.get('title', 'Untitled')
                # Try to get event type title if available
                event_type = booking.get('eventType', {})
                if isinstance(event_type, dict) and event_type.get('title'):
                    title = event_type.get('title', title)
                attendees = booking.get('attendees', [])
                attendee_name = attendees[0].get('name', 'Unknown') if attendees else 'Unknown'
                booking_details.append(f"{title} on {start_time_eastern} with {attendee_name}")
            
            return f"Retrieved bookings at {current_time}. Found {len(bookings)} booking(s) for {filter_email}: {'; '.join(booking_details)}"
        except Exception as e:
            return f"Error retrieving bookings: {str(e)}"
    
    @function_tool()
    async def get_booking(booking_uid: str) -> str:
        """Get details of a specific booking by its UID."""
        try:
            result = await calcom_client.get_booking(booking_uid)
            current_time = format_eastern_time(get_current_eastern_time())
            # Format booking details nicely
            if isinstance(result, dict):
                title = result.get('title', 'Untitled')
                start_utc = result.get('start', '')
                status = result.get('status', 'unknown')
                if start_utc:
                    try:
                        start_eastern = convert_utc_to_eastern(start_utc)
                    except:
                        start_eastern = start_utc
                else:
                    start_eastern = 'Unknown time'
                return f"Retrieved booking details at {current_time}. {title} - {start_eastern} (Status: {status})"
            return f"Retrieved booking details at {current_time}. {str(result)}"
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                return f"Error retrieving booking - booking not found. Please check the booking UID: {booking_uid}"
            return f"Error retrieving booking: {error_msg}"
    
    @function_tool()
    async def create_connect_meeting(start_time_eastern: str, attendee_name: str, attendee_email: Optional[str] = None) -> str:
        """Create a Connect meeting. start_time_eastern should be in Eastern Time format (e.g., '2026-01-10 09:00' or '01/10/2026 9:00 AM'). If attendee_email is not provided, uses default email. The conversation history will be automatically included in the meeting notes."""
        try:
            email = attendee_email or default_email
            if not email:
                return "Error: No email address provided. Please provide an email address for the attendee."
            start_time_utc = convert_to_utc_iso(start_time_eastern)
            
            # Get conversation history from agent if available
            notes = None
            current_agent = agent_instance
            # If agent_instance is None, try to get it from the entrypoint's stored instance
            if not current_agent:
                try:
                    # Try to access the global agent instance from agent.py
                    # Import here to avoid circular imports
                    import importlib
                    agent_module = importlib.import_module('agent')
                    if agent_module and hasattr(agent_module, '_agent_instance'):
                        current_agent = agent_module._agent_instance
                except Exception as e:
                    import logging
                    logger = logging.getLogger("agent-Alex-2f2")
                    logger.debug(f"Could not access global agent instance: {e}")
            
            if current_agent and hasattr(current_agent, 'chat_ctx') and current_agent.chat_ctx:
                try:
                    messages = list(current_agent.chat_ctx.messages)
                    if messages:
                        # Format conversation history for meeting notes
                        conversation_lines = []
                        conversation_lines.append("=== Conversation History ===")
                        for msg in messages:
                            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                                role = msg.role
                                content = msg.content
                                # Handle list content (may contain images)
                                if isinstance(content, list):
                                    from livekit.agents.llm import ImageContent
                                    text_parts = [str(item) for item in content if not isinstance(item, ImageContent)]
                                    content = " ".join(text_parts) if text_parts else "[Image shared]"
                                # Format message
                                role_label = "User" if role == "user" else "Assistant"
                                conversation_lines.append(f"\n{role_label}: {str(content)}")
                        notes = "\n".join(conversation_lines)
                except Exception as e:
                    import logging
                    logger = logging.getLogger("agent-Alex-2f2")
                    logger.warning(f"Could not extract conversation history for meeting notes: {e}")
            
            result = await calcom_client.create_booking(
                event_type_id=CONNECT_MEETING_EVENT_TYPE_ID, 
                start_time=start_time_utc, 
                attendee_name=attendee_name, 
                attendee_email=email,
                notes=notes
            )
            # Client now returns the booking data directly (extracted from 'data' field)
            current_time = format_eastern_time(get_current_eastern_time())
            # Extract booking details for confirmation
            booking_start_utc = result.get('start', start_time_utc) if isinstance(result, dict) else start_time_utc
            # Convert to Eastern for display
            try:
                booking_start_eastern = convert_utc_to_eastern(booking_start_utc)
            except:
                booking_start_eastern = booking_start_utc
            booking_uid = result.get('uid', '') if isinstance(result, dict) else ''
            return f"Connect meeting scheduled at {current_time}. Meeting created successfully for {booking_start_eastern}. Booking UID: {booking_uid}"
        except ValueError as e:
            return f"Error creating Connect meeting - invalid time format: {str(e)}. Please provide time in Eastern Time format (e.g., '2026-01-10 09:00' or '01/10/2026 9:00 AM')."
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg or "bad request" in error_msg.lower():
                return f"Error creating Connect meeting - bad request. Please check: 1) Time format is correct (Eastern Time), 2) Date is in the future, 3) Email is valid. Details: {error_msg}"
            return f"Error creating Connect meeting: {error_msg}"
    
    @function_tool()
    async def create_discover_meeting(start_time_eastern: str, attendee_name: str, attendee_email: Optional[str] = None) -> str:
        """Create a Discover meeting. start_time_eastern should be in Eastern Time format (e.g., '2026-01-10 10:00' or '01/10/2026 10:00 AM'). If attendee_email is not provided, uses default email. The conversation history will be automatically included in the meeting notes."""
        try:
            email = attendee_email or default_email
            if not email:
                return "Error: No email address provided. Please provide an email address for the attendee."
            start_time_utc = convert_to_utc_iso(start_time_eastern)
            
            # Get conversation history from agent if available
            notes = None
            current_agent = agent_instance
            # If agent_instance is None, try to get it from the entrypoint's stored instance
            if not current_agent:
                try:
                    # Try to access the global agent instance from agent.py
                    # Import here to avoid circular imports
                    import importlib
                    agent_module = importlib.import_module('agent')
                    if agent_module and hasattr(agent_module, '_agent_instance'):
                        current_agent = agent_module._agent_instance
                except Exception as e:
                    import logging
                    logger = logging.getLogger("agent-Alex-2f2")
                    logger.debug(f"Could not access global agent instance: {e}")
            
            if current_agent and hasattr(current_agent, 'chat_ctx') and current_agent.chat_ctx:
                try:
                    messages = list(current_agent.chat_ctx.messages)
                    if messages:
                        # Format conversation history for meeting notes
                        conversation_lines = []
                        conversation_lines.append("=== Conversation History ===")
                        for msg in messages:
                            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                                role = msg.role
                                content = msg.content
                                # Handle list content (may contain images)
                                if isinstance(content, list):
                                    from livekit.agents.llm import ImageContent
                                    text_parts = [str(item) for item in content if not isinstance(item, ImageContent)]
                                    content = " ".join(text_parts) if text_parts else "[Image shared]"
                                # Format message
                                role_label = "User" if role == "user" else "Assistant"
                                conversation_lines.append(f"\n{role_label}: {str(content)}")
                        notes = "\n".join(conversation_lines)
                except Exception as e:
                    import logging
                    logger = logging.getLogger("agent-Alex-2f2")
                    logger.warning(f"Could not extract conversation history for meeting notes: {e}")
            
            result = await calcom_client.create_booking(
                event_type_id=DISCOVER_MEETING_EVENT_TYPE_ID, 
                start_time=start_time_utc, 
                attendee_name=attendee_name, 
                attendee_email=email,
                notes=notes
            )
            # Client now returns the booking data directly (extracted from 'data' field)
            current_time = format_eastern_time(get_current_eastern_time())
            # Extract booking details for confirmation
            booking_start_utc = result.get('start', start_time_utc) if isinstance(result, dict) else start_time_utc
            # Convert to Eastern for display
            try:
                booking_start_eastern = convert_utc_to_eastern(booking_start_utc)
            except:
                booking_start_eastern = booking_start_utc
            booking_uid = result.get('uid', '') if isinstance(result, dict) else ''
            return f"Discover meeting scheduled at {current_time}. Meeting created successfully for {booking_start_eastern}. Booking UID: {booking_uid}"
        except ValueError as e:
            return f"Error creating Discover meeting - invalid time format: {str(e)}. Please provide time in Eastern Time format (e.g., '2026-01-10 10:00' or '01/10/2026 10:00 AM')."
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg or "bad request" in error_msg.lower():
                return f"Error creating Discover meeting - bad request. Please check: 1) Time format is correct (Eastern Time), 2) Date is in the future, 3) Email is valid. Details: {error_msg}"
            return f"Error creating Discover meeting: {error_msg}"
    
    @function_tool()
    async def reschedule_booking(booking_uid: Optional[str] = None, old_date_time_eastern: Optional[str] = None, new_start_time_eastern: str = "", reason: Optional[str] = None) -> str:
        """Reschedule a booking. Provide: 1) booking_uid (the booking ID), OR 2) old_date_time_eastern (the current date/time of the booking in Eastern Time). Also provide new_start_time_eastern (the new date/time in Eastern Time format). Note: This creates a new booking and cancels the old one."""
        try:
            if not new_start_time_eastern:
                return "Error: new_start_time_eastern is required. Please provide the new date and time for the rescheduled booking."
            
            current_time = format_eastern_time(get_current_eastern_time())
            booking_uid_to_reschedule = booking_uid
            
            # If old date/time provided instead of UID, search for the booking first
            if not booking_uid_to_reschedule and old_date_time_eastern:
                # Get email for search
                filter_email = _email_state.get("email")
                if not filter_email and agent_instance and hasattr(agent_instance, 'user_email'):
                    filter_email = agent_instance.user_email
                if not filter_email:
                    filter_email = default_email
                
                if not filter_email:
                    return "Error: No email address provided. Cannot search for booking without email."
                
                # Get all upcoming bookings
                result = await calcom_client.get_all_bookings(take=100, status="upcoming", email=filter_email)
                bookings = result.get('bookings', [])
                
                # Parse the old date/time provided by user (Eastern Time)
                try:
                    EASTERN_TZ = pytz.timezone("America/New_York")
                    # Convert user's Eastern time string to a datetime object in Eastern Time
                    target_time_utc_str = convert_to_utc_iso(old_date_time_eastern)
                    target_dt_utc = datetime.fromisoformat(target_time_utc_str.replace('Z', '+00:00'))
                    if target_dt_utc.tzinfo is None:
                        target_dt_utc = pytz.UTC.localize(target_dt_utc)
                    target_dt_eastern = target_dt_utc.astimezone(EASTERN_TZ)
                    
                    target_date = target_dt_eastern.date()
                    target_hour = target_dt_eastern.hour
                    target_minute = target_dt_eastern.minute
                except Exception as e:
                    return f"Error parsing old date/time '{old_date_time_eastern}': {str(e)}. Please provide time in Eastern Time format."
                
                # Find matching booking by date and time (compare both in Eastern Time)
                matching_bookings = []
                for booking in bookings:
                    if booking.get('status', '').lower() == 'cancelled':
                        continue
                    start_utc = booking.get('start', '')
                    if start_utc:
                        try:
                            # Convert booking's UTC time to Eastern Time for comparison
                            booking_dt_utc = datetime.fromisoformat(start_utc.replace('Z', '+00:00').replace('.000', ''))
                            if booking_dt_utc.tzinfo is None:
                                booking_dt_utc = pytz.UTC.localize(booking_dt_utc)
                            booking_dt_eastern = booking_dt_utc.astimezone(EASTERN_TZ)
                            
                            booking_date = booking_dt_eastern.date()
                            booking_hour = booking_dt_eastern.hour
                            booking_minute = booking_dt_eastern.minute
                            
                            if booking_date == target_date:
                                time_diff = abs((booking_hour * 60 + booking_minute) - (target_hour * 60 + target_minute))
                                if time_diff <= 30:  # Within 30 minutes
                                    matching_bookings.append((booking, time_diff))
                        except Exception as e:
                            import logging
                            logger = logging.getLogger("agent-Alex-2f2")
                            logger.error(f"Error processing booking time: {e}")
                            continue
                
                if not matching_bookings:
                    return f"No upcoming booking found for {old_date_time_eastern} Eastern Time. Please check the date and time, or provide the booking UID directly."
                
                matching_bookings.sort(key=lambda x: x[1])
                booking_uid_to_reschedule = matching_bookings[0][0].get('uid')
                
                if not booking_uid_to_reschedule:
                    return f"Found booking for {old_date_time_eastern} but could not get booking UID. Please provide the booking UID directly."
            
            if not booking_uid_to_reschedule:
                return "Error: Please provide either booking_uid or old_date_time_eastern to reschedule a booking."
            
            # Convert new time to UTC
            new_start_time_utc = convert_to_utc_iso(new_start_time_eastern)
            result = await calcom_client.reschedule_booking(booking_uid=booking_uid_to_reschedule, new_start_time=new_start_time_utc, reason=reason)
            
            # Reschedule creates a NEW booking - extract the new booking details
            new_uid = result.get('uid', booking_uid_to_reschedule) if isinstance(result, dict) else booking_uid_to_reschedule
            new_start = result.get('start', new_start_time_utc) if isinstance(result, dict) else new_start_time_utc
            # Convert new start time to Eastern for display
            try:
                new_start_eastern = convert_utc_to_eastern(new_start)
            except:
                new_start_eastern = new_start
            return f"Booking rescheduled at {current_time}. New booking created: {new_start_eastern} (UID: {new_uid}). The original booking has been cancelled."
        except ValueError as e:
            return f"Error rescheduling booking - invalid time format: {str(e)}. Please provide time in Eastern Time format."
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg or "bad request" in error_msg.lower():
                return f"Error rescheduling booking - bad request. Please check: 1) Time format is correct (Eastern Time), 2) Date is in the future, 3) Booking UID is valid. Details: {error_msg}"
            return f"Error rescheduling booking: {error_msg}"
    
    @function_tool()
    async def cancel_booking(booking_uid: Optional[str] = None, date_time_eastern: Optional[str] = None, reason: Optional[str] = None) -> str:
        """Cancel a booking. You can provide either: 1) booking_uid (the booking ID), OR 2) date_time_eastern (date and time in Eastern Time format like '2026-07-15 2:00 PM' or 'July 15, 2026 at 2:00 PM'). If date_time_eastern is provided, the system will search for the booking by date and time first."""
        try:
            current_time = format_eastern_time(get_current_eastern_time())
            booking_uid_to_cancel = booking_uid
            
            # If date/time provided instead of UID, search for the booking first
            if not booking_uid_to_cancel and date_time_eastern:
                # Get email for search
                filter_email = _email_state.get("email")
                if not filter_email and agent_instance and hasattr(agent_instance, 'user_email'):
                    filter_email = agent_instance.user_email
                if not filter_email:
                    filter_email = default_email
                
                if not filter_email:
                    return "Error: No email address provided. Cannot search for booking without email."
                
                # Get all upcoming bookings
                result = await calcom_client.get_all_bookings(take=100, status="upcoming", email=filter_email)
                bookings = result.get('bookings', [])
                
                # Parse the date/time provided by user (Eastern Time)
                # Parse user's Eastern time input to get date and time components
                try:
                    # Convert user's Eastern time string to a datetime object in Eastern Time
                    from datetime import datetime
                    import pytz
                    EASTERN_TZ = pytz.timezone("America/New_York")
                    
                    # Try to parse the user's input as Eastern Time
                    # First convert to UTC ISO to get a proper datetime, then convert back to Eastern
                    target_time_utc_str = convert_to_utc_iso(date_time_eastern)
                    target_dt_utc = datetime.fromisoformat(target_time_utc_str.replace('Z', '+00:00'))
                    if target_dt_utc.tzinfo is None:
                        target_dt_utc = pytz.UTC.localize(target_dt_utc)
                    target_dt_eastern = target_dt_utc.astimezone(EASTERN_TZ)
                    
                    target_date = target_dt_eastern.date()
                    target_hour = target_dt_eastern.hour
                    target_minute = target_dt_eastern.minute
                except Exception as e:
                    return f"Error parsing date/time '{date_time_eastern}': {str(e)}. Please provide time in Eastern Time format (e.g., '2026-07-15 2:00 PM' or 'July 15, 2026 at 2:00 PM')."
                
                # Find matching booking by date and time (compare both in Eastern Time)
                matching_bookings = []
                for booking in bookings:
                    if booking.get('status', '').lower() == 'cancelled':
                        continue
                    start_utc = booking.get('start', '')
                    if start_utc:
                        try:
                            # Convert booking's UTC time to Eastern Time for comparison
                            booking_dt_utc = datetime.fromisoformat(start_utc.replace('Z', '+00:00').replace('.000', ''))
                            if booking_dt_utc.tzinfo is None:
                                booking_dt_utc = pytz.UTC.localize(booking_dt_utc)
                            booking_dt_eastern = booking_dt_utc.astimezone(EASTERN_TZ)
                            
                            booking_date = booking_dt_eastern.date()
                            booking_hour = booking_dt_eastern.hour
                            booking_minute = booking_dt_eastern.minute
                            
                            # Match by date and approximate time (within 30 minutes)
                            if booking_date == target_date:
                                time_diff = abs((booking_hour * 60 + booking_minute) - (target_hour * 60 + target_minute))
                                if time_diff <= 30:  # Within 30 minutes
                                    matching_bookings.append((booking, time_diff))
                        except Exception as e:
                            import logging
                            logger = logging.getLogger("agent-Alex-2f2")
                            logger.error(f"Error processing booking time: {e}")
                            continue
                
                if not matching_bookings:
                    return f"No upcoming booking found for {date_time_eastern} Eastern Time. Please check the date and time, or provide the booking UID directly."
                
                # Sort by time difference (closest match first)
                matching_bookings.sort(key=lambda x: x[1])
                booking_uid_to_cancel = matching_bookings[0][0].get('uid')
                
                if not booking_uid_to_cancel:
                    return f"Found booking for {date_time_eastern} but could not get booking UID. Please provide the booking UID directly."
            
            if not booking_uid_to_cancel:
                return "Error: Please provide either booking_uid or date_time_eastern to cancel a booking."
            
            # First verify the booking exists and get its details
            try:
                existing_booking = await calcom_client.get_booking(booking_uid_to_cancel)
                existing_status = existing_booking.get('status', '') if isinstance(existing_booking, dict) else ''
                if existing_status.lower() == 'cancelled':
                    return f"This booking is already cancelled. No action needed."
            except:
                pass  # Continue with cancel attempt even if get fails
            
            # Cancel the booking
            result = await calcom_client.cancel_booking(booking_uid=booking_uid_to_cancel, reason=reason)
            
            # Extract booking details for confirmation
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                title = result.get('title', 'Untitled')
                start_utc = result.get('start', '')
                
                if status.lower() == 'cancelled':
                    # Convert start time to Eastern for display
                    if start_utc:
                        try:
                            start_eastern = convert_utc_to_eastern(start_utc)
                        except:
                            start_eastern = start_utc
                    else:
                        start_eastern = 'Unknown time'
                    
                    cancellation_reason = result.get('cancellationReason', '')
                    reason_text = f" Reason: {cancellation_reason}" if cancellation_reason else ""
                    return f"Booking cancelled successfully at {current_time}. {title} on {start_eastern} has been cancelled.{reason_text}"
                else:
                    return f"Booking cancellation processed at {current_time}. Status: {status}. Please verify the cancellation was successful."
            else:
                return f"Booking cancellation processed at {current_time}. Response: {str(result)}"
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                return f"Error canceling booking - booking not found. Please check the booking UID or date/time provided."
            return f"Error canceling booking: {error_msg}"
    
    @function_tool()
    async def add_guests_to_booking(booking_uid: str, guest_emails: List[str], guest_names: List[str]) -> str:
        """Add guests to a booking. Provide lists of emails and names (must match in order)."""
        try:
            if len(guest_emails) != len(guest_names):
                return "Error: Number of emails must match number of names"
            guests = [{"email": email, "name": name} for email, name in zip(guest_emails, guest_names)]
            result = await calcom_client.add_guests(booking_uid=booking_uid, guests=guests)
            current_time = format_eastern_time(get_current_eastern_time())
            return f"Guests added at {current_time}. {str(result)}"
        except Exception as e:
            return f"Error adding guests: {str(e)}"
    
    @function_tool()
    async def get_current_time() -> str:
        """Get the current time in Eastern Time zone."""
        current_time = get_current_eastern_time()
        return format_eastern_time(current_time)
    
    return [
        get_all_bookings, get_booking, create_connect_meeting, create_discover_meeting,
        reschedule_booking, cancel_booking, add_guests_to_booking, get_current_time,
    ]

