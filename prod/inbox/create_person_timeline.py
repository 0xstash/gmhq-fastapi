import json
import os
from datetime import datetime, timezone
from dateutil import parser
import re


class PersonTimelineCreator:
    def __init__(self):
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Define file paths relative to the script location
        self.email_file = os.path.join(script_dir, "primary_emails.json")
        self.calendar_file = os.path.join(script_dir, "calendar_events.json")
        self.output_file = os.path.join(script_dir, "person_timeline.json")
        self.your_domains = ["troylabs.io", "godmodehq.com"]  # Your email domains

    def extract_email_addresses(self, text):
        """Extract email addresses from text strings"""
        if not text:
            return []
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return re.findall(email_pattern, text)

    def get_email_domain(self, email):
        """Extract domain from email address"""
        if not email or "@" not in email:
            return ""
        return email.split("@")[1].lower()

    def is_your_email(self, email):
        """Check if the email belongs to you"""
        if not email:
            return False
        domain = self.get_email_domain(email)
        return domain in self.your_domains

    def create_person_timeline(self):
        """Create person-centric timeline of all interactions up to current time"""
        try:
            # Load email data
            if not os.path.exists(self.email_file):
                print(f"Email file {self.email_file} not found!")
                return

            with open(self.email_file, "r", encoding="utf-8") as f:
                email_data = json.load(f)

            # Load calendar data
            if not os.path.exists(self.calendar_file):
                print(f"Calendar file {self.calendar_file} not found!")
                return

            with open(self.calendar_file, "r", encoding="utf-8") as f:
                calendar_data = json.load(f)

            # Extract threads and events
            email_threads = email_data.get("threads", [])
            calendar_events = calendar_data.get("events", [])

            # Get current time for filtering future events
            now = datetime.now(timezone.utc)

            # Create a dictionary to hold person data
            people = {}

            # Process email threads into person data structure
            print("Processing email threads...")
            for thread in email_threads:
                thread_id = thread.get("thread_id")
                messages = thread.get("messages", [])

                # Skip empty threads
                if not messages:
                    continue

                # Get all participants in this thread
                all_participants = set()
                for message in messages:
                    # Extract from 'from' field
                    from_emails = self.extract_email_addresses(message.get("from", ""))
                    for email in from_emails:
                        all_participants.add(email.lower())

                    # Extract from 'to' field
                    to_emails = self.extract_email_addresses(message.get("to", ""))
                    for email in to_emails:
                        all_participants.add(email.lower())

                # Remove your own emails from participants
                external_participants = set()
                for email in all_participants:
                    if not self.is_your_email(email):
                        external_participants.add(email)

                # Process each message in the thread
                for message in messages:
                    message_date = message.get("date", "")
                    try:
                        # Parse date for sorting
                        parsed_date = parser.parse(message_date)
                        # Make sure parsed_date is timezone-aware
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)

                        # Skip future messages (shouldn't exist but just in case)
                        if parsed_date > now:
                            continue

                        timestamp = parsed_date.isoformat()
                    except Exception as e:
                        print(f"Error parsing date '{message_date}': {str(e)}")
                        continue

                    # Get sender and determine direction
                    sender_emails = self.extract_email_addresses(
                        message.get("from", "")
                    )
                    if not sender_emails:
                        continue

                    sender_email = sender_emails[0].lower()
                    is_inbound = not self.is_your_email(sender_email)

                    # Create interaction item
                    interaction = {
                        "id": message.get("id", ""),
                        "thread_id": thread_id,
                        "timestamp": timestamp,
                        "date": message_date,
                        "type": "email",
                        "direction": "inbound" if is_inbound else "outbound",
                        "subject": message.get("subject", ""),
                        "body": message.get("body", ""),
                        "snippet": message.get("snippet", ""),
                        "from": message.get("from", ""),
                        "to": message.get("to", ""),
                        "participants": list(all_participants),
                    }

                    # Add this interaction to each external participant's timeline
                    for email in external_participants:
                        if email not in people:
                            # Initialize new person
                            people[email] = {
                                "email": email,
                                "name": "",  # Will be filled in later if available
                                "company": "",  # Will be filled in later if available
                                "interactions": [],
                                "last_interaction_date": "",
                                "interaction_count": 0,
                                "email_count": 0,
                                "event_count": 0,
                            }

                        # Add interaction to person's timeline
                        people[email]["interactions"].append(interaction)
                        people[email]["email_count"] += 1
                        people[email]["interaction_count"] += 1

                        # Update name if it's blank and we can infer it
                        if not people[email]["name"]:
                            from_name = message.get("from", "")
                            if email in from_name.lower():
                                name_part = from_name.split("<")[0].strip()
                                if name_part:
                                    people[email]["name"] = name_part

            # Process calendar events into person data structure
            print("Processing calendar events...")
            for event in calendar_events:
                event_id = event.get("id", "")
                summary = event.get("summary", "")
                description = event.get("description", "")
                start_time = event.get("start_time", "")
                end_time = event.get("end_time", "")
                location = event.get("location", "")

                # Skip events without valid timestamps
                if not start_time:
                    continue

                try:
                    # Parse date for sorting
                    parsed_date = parser.parse(start_time)
                    # Make sure parsed_date is timezone-aware
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)

                    # Skip future events
                    if parsed_date > now:
                        # Optional: Comment out or remove this line to reduce output noise
                        # print(f"Skipping future event: {start_time}")
                        continue

                    timestamp = parsed_date.isoformat()
                except Exception as e:
                    print(f"Error parsing date '{start_time}': {str(e)}")
                    continue

                # Get all attendees' emails
                attendee_emails = set()
                for attendee in event.get("attendees", []):
                    if "email" in attendee and attendee["email"]:
                        email = attendee["email"].lower()
                        if not self.is_your_email(email):
                            attendee_emails.add(email)

                # Also check description for additional emails
                description_emails = self.extract_email_addresses(description)
                for email in description_emails:
                    email = email.lower()
                    if not self.is_your_email(email):
                        attendee_emails.add(email)

                # Create interaction item
                interaction = {
                    "id": event_id,
                    "timestamp": timestamp,
                    "date": start_time,
                    "end_time": end_time,
                    "type": "calendar",
                    "summary": summary,
                    "description": description,
                    "location": location,
                    "status": event.get("status", ""),
                    "event_status": event.get("event_status", ""),
                    "attendees": event.get("attendees", []),
                    "organizer": event.get("organizer", {}),
                    "is_all_day": event.get("is_all_day", False),
                }

                # Add this interaction to each attendee's timeline
                for email in attendee_emails:
                    if email not in people:
                        # Initialize new person
                        people[email] = {
                            "email": email,
                            "name": "",
                            "company": "",
                            "interactions": [],
                            "last_interaction_date": "",
                            "interaction_count": 0,
                            "email_count": 0,
                            "event_count": 0,
                        }

                    # Add interaction to person's timeline
                    people[email]["interactions"].append(interaction)
                    people[email]["event_count"] += 1
                    people[email]["interaction_count"] += 1

                    # Update name if we can find it in attendees
                    if not people[email]["name"]:
                        for attendee in event.get("attendees", []):
                            if attendee.get("email", "").lower() == email:
                                name = attendee.get("name", "")
                                if name:
                                    people[email]["name"] = name
                                    break

            # Sort each person's interactions by timestamp
            for email, person in people.items():
                person["interactions"].sort(key=lambda x: x["timestamp"], reverse=True)

                # Update last interaction date
                if person["interactions"]:
                    person["last_interaction_date"] = person["interactions"][0][
                        "timestamp"
                    ]

            # Sort people by most recent interaction
            people_list = list(people.values())
            people_list.sort(key=lambda x: x["last_interaction_date"], reverse=True)

            # Create final output data structure
            timeline_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_people": len(people_list),
                "people": people_list,
            }

            # Save to file
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(timeline_data, f, indent=2, ensure_ascii=False)

            print(f"Successfully created person timeline file: {self.output_file}")

            return timeline_data

        except Exception as e:
            print(f"Error creating person timeline: {e}")
            raise


def main():
    creator = PersonTimelineCreator()
    try:
        creator.create_person_timeline()
    except Exception as e:
        print(f"Failed to create person timeline: {e}")
        raise


if __name__ == "__main__":
    main()
