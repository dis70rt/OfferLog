import base64
import logging

import html2text

logger = logging.getLogger(__name__)

_h2t = html2text.HTML2Text()
_h2t.ignore_links = False
_h2t.ignore_images = True
_h2t.body_width = 0  # Don't wrap lines


def get_email_body(payload):
    """Recursively extract plain text (or HTML fallback) body from the Gmail API payload."""
    text_body = ""
    html_body = ""

    def decode_data(data):
        if not data:
            return ""
        # Pad base64 string if necessary
        data += "=" * ((4 - len(data) % 4) % 4)
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    def extract(part):
        nonlocal text_body, html_body
        mime_type = part.get('mimeType', '')

        if mime_type == 'text/plain':
            text_body += decode_data(part.get('body', {}).get('data'))
        elif mime_type == 'text/html':
            html_body += decode_data(part.get('body', {}).get('data'))

        if 'parts' in part:
            for subpart in part['parts']:
                extract(subpart)

    extract(payload)

    if text_body:
        return text_body

    if html_body:
        return _h2t.handle(html_body).strip()

    return ""
