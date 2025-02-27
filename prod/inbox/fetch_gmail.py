from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime
import json
from collections import defaultdict
import base64
import email
from email.utils import parsedate_to_datetime


class GmailFetcher:
    def __init__(self):
        # Allow OAuth to work in development
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.creds = None
        self.credentials_file = (
            "client_secrets.json"  # Make sure this matches your downloaded file name
        )
        self.output_file = "primary_emails.json"

    def authenticate(self):
        """Handle Gmail authentication using OAuth"""
        try:
            # Check for existing token
            if os.path.exists("token.pickle"):
                print("Found existing token, attempting to load...")
                with open("token.pickle", "rb") as token:
                    self.creds = pickle.load(token)

            # If no valid credentials available, let user login
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

                    # Save credentials for future use
                    print("Saving new token...")
                    with open("token.pickle", "wb") as token:
                        pickle.dump(self.creds, token)

        except Exception as e:
            print(f"\nAuthentication error: {e}")
            print("\nPlease ensure:")
            print(
                f"1. You have downloaded the OAuth client ID credentials as '{self.credentials_file}'"
            )
            print("2. The credentials are for a Desktop application")
            print("3. Gmail API is enabled in your Google Cloud Console")
            raise

    def list_labels(self):
        """List all available Gmail labels"""
        try:
            service = build("gmail", "v1", credentials=self.creds)
            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            print("\nAvailable labels:")
            for label in labels:
                print(f"Name: {label['name']}, ID: {label['id']}")

            return labels

        except Exception as e:
            print(f"Error fetching labels: {e}")
            return []

    def get_email_body(self, payload):
        """Extract only plain text body from email payload"""
        body = ""

        if payload.get("body") and payload["body"].get("data"):
            # Handle single-part message
            data = base64.urlsafe_b64decode(
                payload["body"]["data"].encode("UTF-8")
            ).decode("UTF-8")
            if payload.get("mimeType") == "text/plain":
                body = data

        elif payload.get("parts"):
            # Handle multipart message
            for part in payload["parts"]:
                mimeType = part.get("mimeType")
                if part.get("body") and part["body"].get("data"):
                    data = base64.urlsafe_b64decode(
                        part["body"]["data"].encode("UTF-8")
                    ).decode("UTF-8")
                    if mimeType == "text/plain":
                        body = data
                        break  # Stop after finding plain text

                # Handle nested multipart messages
                if part.get("parts"):
                    nested_body = self.get_email_body(part)
                    if nested_body:
                        body = nested_body
                        break

        return body

    def fetch_and_save_primary_emails(self, limit=20):
        """Fetch both received and sent email threads and save to JSON file"""
        try:
            print("Authenticating...")
            self.authenticate()

            print("Building Gmail service...")
            service = build("gmail", "v1", credentials=self.creds)

            # First, get primary inbox messages
            print(f"Fetching inbox messages...")
            inbox_results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=limit * 2,  # Increased to account for sent messages too
                    labelIds=["INBOX", "CATEGORY_PERSONAL"],
                )
                .execute()
            )
            inbox_messages = inbox_results.get("messages", [])

            # Next, get sent messages
            print(f"Fetching sent messages...")
            sent_results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=limit * 2,  # Doubled to ensure we get enough
                    labelIds=["SENT"],
                )
                .execute()
            )
            sent_messages = sent_results.get("messages", [])

            # Combine messages from both sources
            all_message_ids = {}

            # Add inbox messages first
            for message in inbox_messages:
                all_message_ids[message["id"]] = message

            # Add sent messages
            for message in sent_messages:
                all_message_ids[message["id"]] = message

            combined_messages = list(all_message_ids.values())

            threads = defaultdict(list)

            for message in combined_messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )

                headers = msg["payload"]["headers"]
                body_content = self.get_email_body(msg["payload"])

                email_data = {
                    "id": msg["id"],
                    "subject": next(
                        (h["value"] for h in headers if h["name"] == "Subject"),
                        "No subject",
                    ),
                    "from": next(
                        (h["value"] for h in headers if h["name"] == "From"), "Unknown"
                    ),
                    "to": next(
                        (h["value"] for h in headers if h["name"] == "To"), "Unknown"
                    ),
                    "date": next(
                        (h["value"] for h in headers if h["name"] == "Date"), "Unknown"
                    ),
                    "snippet": msg.get("snippet", ""),
                    "body": body_content,
                    "labels": msg.get("labelIds", []),
                }

                thread_id = msg["threadId"]
                threads[thread_id].append(email_data)
                print(f"Processed email: {email_data['subject']}")

            # Convert threads to list and sort by the most recent email in each thread
            thread_list = []
            for thread_id, messages in threads.items():
                # Sort messages within thread by date using email.utils parser
                messages.sort(
                    key=lambda x: parsedate_to_datetime(x["date"]),
                    reverse=True,
                )

                thread_list.append(
                    {
                        "thread_id": thread_id,
                        "subject": messages[0]["subject"],
                        "messages": messages,
                        "message_count": len(messages),
                        "latest_date": messages[0]["date"],
                        "participants": list(
                            set(
                                [m["from"] for m in messages]
                                + [m["to"] for m in messages]
                            )
                        ),
                    }
                )

            # Sort threads by the date of their most recent message
            thread_list.sort(
                key=lambda x: parsedate_to_datetime(x["latest_date"]),
                reverse=True,
            )

            output_data = {
                "timestamp": datetime.now().isoformat(),
                "total_threads": len(thread_list),
                "threads": thread_list,
            }

            # Save to JSON file
            print(f"\nSaving to {self.output_file}...")
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(
                f"\nSuccessfully saved {len(thread_list)} email threads to {self.output_file}"
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise  # Add this to see the full error traceback


def main():
    fetcher = GmailFetcher()
    try:
        fetcher.fetch_and_save_primary_emails()
    except Exception as e:
        print(f"Failed to fetch emails: {e}")
        raise  # Add this to see the full error traceback


if __name__ == "__main__":
    main()
