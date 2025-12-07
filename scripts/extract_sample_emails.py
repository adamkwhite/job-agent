#!/usr/bin/env python3
"""Extract sample emails for parser development"""

import email
import imaplib
import json
import os
from email.header import decode_header

from dotenv import load_dotenv

load_dotenv()

# Load email settings
with open("config/email-settings.json") as f:
    settings = json.load(f)

# Connect to email
mail = imaplib.IMAP4_SSL(settings["imap"]["server"], settings["imap"]["port"])
password = os.getenv("GMAIL_APP_PASSWORD")
if not password:
    raise ValueError("GMAIL_APP_PASSWORD environment variable not set")
mail.login(settings["imap"]["username"], password)
mail.select(settings["imap"]["mailbox"])

# Search for unread emails
_, message_ids = mail.search(None, "UNSEEN")

# Track saved emails
saved_emails = {
    "mechanical": False,
    "titan_haptics": False,
    "intact": False,
    "health_tech": False,
    "work_in_tech": False,
}

if message_ids[0]:
    for msg_id in message_ids[0].split()[:20]:  # Check first 20 unread
        _, msg_data = mail.fetch(msg_id, "(RFC822)")
        # msg_data is a list of tuples, each tuple is (flags, message_bytes)
        if msg_data and isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
            msg_bytes = msg_data[0][1]
            if isinstance(msg_bytes, bytes):
                msg = email.message_from_bytes(msg_bytes)
            else:
                continue
        else:
            continue

        # Decode subject
        subject_parts = decode_header(msg["Subject"])
        subject = ""
        for part, encoding in subject_parts:
            if isinstance(part, bytes):
                subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                subject += str(part)

        from_addr = msg["From"]

        # Extract body
        body_html = ""
        body_text = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_html = payload.decode("utf-8", errors="ignore")
            elif part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_text = payload.decode("utf-8", errors="ignore")

        # Save mechanical engineering emails
        if "mechanical engineer" in subject.lower() and not saved_emails["mechanical"]:
            os.makedirs("data/sample_emails", exist_ok=True)
            with open("data/sample_emails/mechanical_engineer.html", "w") as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- From: {from_addr} -->\n")
                f.write(body_html or body_text)
            print(f"✓ Saved mechanical engineering email: {subject}")
            saved_emails["mechanical"] = True

        # Save TITAN Haptics email
        if "TITAN Haptics" in subject and not saved_emails["titan_haptics"]:
            with open("data/sample_emails/titan_haptics.html", "w") as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- From: {from_addr} -->\n")
                f.write(body_html or body_text)
            print(f"✓ Saved TITAN Haptics email: {subject}")
            saved_emails["titan_haptics"] = True

        # Save Intact email
        if "Intact" in subject and "Manager" in subject and not saved_emails["intact"]:
            with open("data/sample_emails/intact_manager.html", "w") as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- From: {from_addr} -->\n")
                f.write(body_html or body_text)
            print(f"✓ Saved Intact email: {subject}")
            saved_emails["intact"] = True

        # Save Health Tech Reads
        if "Health Tech Reads" in subject and not saved_emails["health_tech"]:
            with open("data/sample_emails/health_tech_reads.html", "w") as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- From: {from_addr} -->\n")
                f.write(body_html or body_text)
            print(f"✓ Saved Health Tech Reads email: {subject}")
            saved_emails["health_tech"] = True

        # Save Work In Tech
        if "Work In Tech" in subject and not saved_emails["work_in_tech"]:
            with open("data/sample_emails/work_in_tech.html", "w") as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- From: {from_addr} -->\n")
                f.write(body_html or body_text)
            print(f"✓ Saved Work In Tech email: {subject}")
            saved_emails["work_in_tech"] = True

        # Break if all found
        if all(saved_emails.values()):
            break

mail.close()
mail.logout()

print(f"\nSaved {sum(saved_emails.values())} sample emails to data/sample_emails/")
print("Not found:", [k for k, v in saved_emails.items() if not v])
