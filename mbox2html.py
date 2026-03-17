#!/usr/bin/env python3
"""Convert an mbox/eml email with inline images to a self-contained HTML file.

Parses MIME multipart/related emails, extracts the HTML body, and replaces
all cid: references with inline base64 data URIs.

Usage: mbox2html.py [options] [message.eml]
       mbox2html.py -b firefox < message.eml
       mbox2html.py -o out.html message.mbox
"""

import argparse
import base64
import email
import email.policy
import os
import re
import subprocess
import sys
import tempfile


def extract_html_and_parts(msg):
    """Walk the MIME tree, return (html_body, {content_id: (mime_type, data)})."""
    html_body = None
    cid_map = {}

    for part in msg.walk():
        content_type = part.get_content_type()
        content_id = part.get("Content-ID", "")
        # Strip angle brackets from Content-ID: <foo> -> foo
        content_id = content_id.strip("<>")

        if content_type == "text/html" and html_body is None:
            html_body = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            html_body = html_body.decode(charset, errors="replace")
        elif content_id and not content_type.startswith("multipart/"):
            payload = part.get_payload(decode=True)
            if payload:
                cid_map[content_id] = (content_type, payload)

    return html_body, cid_map


def inline_cid_references(html, cid_map):
    """Replace cid:xxx references in HTML with data: URIs."""
    def replace_cid(match):
        cid = match.group(1)
        if cid in cid_map:
            mime_type, data = cid_map[cid]
            b64 = base64.b64encode(data).decode("ascii")
            return f"data:{mime_type};base64,{b64}"
        return match.group(0)

    # Match cid: in src="cid:...", url(cid:...), etc.
    return re.sub(r"cid:([^\s\"')\]>]+)", replace_cid, html)


def main():
    parser = argparse.ArgumentParser(
        description="Convert MIME email with inline images to self-contained HTML.")
    parser.add_argument("file", nargs="?", default=None,
                        help="input email file (default: stdin)")
    parser.add_argument("-b", "--browser", metavar="BROWSER",
                        help="open result in BROWSER (e.g. firefox, google-chrome)")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write HTML to FILE instead of stdout")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "rb") as f:
            raw = f.read()
    else:
        raw = sys.stdin.buffer.read()

    # Skip mbox "From " envelope line if present
    if raw.startswith(b"From "):
        idx = raw.find(b"\n")
        if idx >= 0:
            raw = raw[idx + 1:]

    msg = email.message_from_bytes(raw, policy=email.policy.default)

    html_body, cid_map = extract_html_and_parts(msg)

    if html_body is None:
        print("No HTML body found in message.", file=sys.stderr)
        sys.exit(1)

    result = inline_cid_references(html_body, cid_map)

    if args.browser:
        fd, path = tempfile.mkstemp(suffix=".html", prefix="email-")
        with os.fdopen(fd, "w") as f:
            f.write(result)
        subprocess.Popen([args.browser, path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif args.output:
        with open(args.output, "w") as f:
            f.write(result)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
