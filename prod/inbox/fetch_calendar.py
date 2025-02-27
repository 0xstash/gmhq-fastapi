from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta
import json
from typing import List, Dict
import pytz
from dateutil import parser


class CalendarFetcher:
    def __init__(self):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        self.SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        self.creds = None
        self.credentials_file = "client_secrets.json"
        self.output_file = "calendar_events.json"

    def authenticate(self):
        """Handle Google Calendar authentication using OAuth"""
        try:
            if os.path.exists("calendar_token.pickle"):
                print("Found existing token, attempting to load...")
                with open("calendar_token.pickle", "rb") as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    print("Token expired, refreshing...")
                    self.creds.refresh(Request())
                else:
                    print("No valid token found, starting OAuth flow...")
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Missing {self.credentials_file}. Please download OAuth client ID "
                            "credentials from Google Cloud Console."
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                    print("Saving new token...")
                    with open("calendar_token.pickle", "wb") as token:
                        pickle.dump(self.creds, token)

        except Exception as e:
            print(f"\nAuthentication error: {e}")
            raise

    def list_calendars(self):
        """List all available calendars"""
        try:
            service = build("calendar", "v3", credentials=self.creds)
            calendars = service.calendarList().list().execute()

            print("\nAvailable calendars:")
            for calendar in calendars["items"]:
                print(f"Name: {calendar['summary']}, ID: {calendar['id']}")

            return calendars["items"]
        except Exception as e:
            print(f"Error fetching calendars: {e}")
            return []

    def extract_email_addresses(self, text):
        """Extract email addresses from text strings"""
        if not text:
            return []

        # Simple regex-like extraction
        import re

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return re.findall(email_pattern, text)

    def normalize_datetime(self, dt_str):
        """Convert various datetime formats to ISO format"""
        if not dt_str:
            return None

        try:
            dt = parser.parse(dt_str)
            return dt.isoformat()
        except:
            return dt_str

    def fetch_and_save_events(self, weeks_back=4, weeks_forward=0):
        """Fetch calendar events from the past weeks until now and save to JSON file"""
        try:
            print("Authenticating...")
            self.authenticate()

            print("Building Calendar service...")
            service = build("calendar", "v3", credentials=self.creds)

            # Calculate time range
            now = datetime.utcnow()
            start_time = (now - timedelta(weeks=weeks_back)).isoformat() + "Z"
            end_time = now.isoformat() + "Z"

            print(f"\nFetching events from {weeks_back} weeks ago until now...")

            # Get list of calendars
            calendars = self.list_calendars()
            all_events = []

            for calendar in calendars:
                calendar_id = calendar["id"]
                calendar_name = calendar["summary"]

                print(f"\nFetching events from calendar: {calendar_name}")

                events_result = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=start_time,
                        timeMax=end_time,
                        maxResults=2500,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                events = events_result.get("items", [])

                for event in events:
                    # Extract start and end times
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))

                    # Normalize to ISO format
                    start_iso = self.normalize_datetime(start)
                    end_iso = self.normalize_datetime(end)

                    # Extract attendees
                    attendees = event.get("attendees", [])

                    # Extract emails from description for better context
                    description = event.get("description", "")
                    emails_in_description = self.extract_email_addresses(description)

                    # Determine event status relative to now
                    event_status = "upcoming"
                    try:
                        event_start = parser.parse(start)
                        if event_start < now:
                            event_status = "past"
                        elif event_start < now + timedelta(days=1):
                            event_status = "today"
                        elif event_start < now + timedelta(days=7):
                            event_status = "this_week"
                    except:
                        pass

                    # Create structured event data
                    event_data = {
                        "id": event["id"],
                        "calendar_id": calendar_id,
                        "calendar_name": calendar_name,
                        "summary": event.get("summary", "No title"),
                        "description": description,
                        "location": event.get("location", ""),
                        "start_time": start_iso,
                        "end_time": end_iso,
                        "status": event.get("status", ""),
                        "event_status": event_status,  # relative to current time
                        "attendees": [
                            {
                                "email": attendee.get("email", ""),
                                "response_status": attendee.get("responseStatus", ""),
                                "name": attendee.get("displayName", ""),
                                "organizer": attendee.get("organizer", False),
                                "self": attendee.get("self", False),
                            }
                            for attendee in attendees
                        ],
                        "organizer": {
                            "email": event.get("organizer", {}).get("email", ""),
                            "self": event.get("organizer", {}).get("self", False),
                        },
                        "created": event.get("created", ""),
                        "updated": event.get("updated", ""),
                        "html_link": event.get("htmlLink", ""),
                        "is_recurring": "recurringEventId" in event,
                        "recurring_event_id": event.get("recurringEventId", ""),
                        "related_emails": emails_in_description,
                        "is_all_day": "date" in event.get("start", {})
                        and "dateTime" not in event.get("start", {}),
                    }

                    all_events.append(event_data)
                    print(f"Processed event: {event_data['summary']}")

            # Group events by date for easier processing
            events_by_date = {}
            for event in all_events:
                try:
                    date_key = parser.parse(event["start_time"]).strftime("%Y-%m-%d")
                    if date_key not in events_by_date:
                        events_by_date[date_key] = []
                    events_by_date[date_key].append(event)
                except:
                    # If date parsing fails, add to 'unknown' category
                    if "unknown" not in events_by_date:
                        events_by_date["unknown"] = []
                    events_by_date["unknown"].append(event)

            # Save to JSON file with enhanced structure
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "date_range": {
                    "start": start_time,
                    "end": end_time,
                    "weeks_back": weeks_back,
                    "weeks_forward": weeks_forward,
                },
                "total_events": len(all_events),
                "events_by_status": {
                    "past": [e for e in all_events if e["event_status"] == "past"],
                    "today": [e for e in all_events if e["event_status"] == "today"],
                    "this_week": [
                        e for e in all_events if e["event_status"] == "this_week"
                    ],
                    "upcoming": [
                        e for e in all_events if e["event_status"] == "upcoming"
                    ],
                },
                "events_by_date": events_by_date,
                "events": all_events,
            }

            # Save to JSON file
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(
                f"\nSuccessfully saved {len(all_events)} events to {self.output_file}"
            )

            return output_data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise


def main():
    fetcher = CalendarFetcher()
    try:
        fetcher.fetch_and_save_events(weeks_back=4, weeks_forward=0)
    except Exception as e:
        print(f"Failed to fetch calendar events: {e}")
        raise


if __name__ == "__main__":
    main()
