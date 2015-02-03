"""
Create and manipulate mime messages, handling attachments and common utility
operations for sending emails.

Many of these functions are used only by ``mailtools.mailer``, however may have
some more general use too.
"""

from __future__ import with_statement

import mimetypes
import re
import os

from email import message_from_string
from email.encoders import encode_base64
from email.header import Header
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


__all__ = 'add_attachments', 'attachment_from_file', 'attachment_from_string',\
          'split_headers', 'make_header', 'extract_recipients', 'strip_name'


def add_attachments(mime_body, attachments):
    """
    Return a container MIME object with the given body and attachments
    attached. If there are no attachments, the original mime_body is returned -
    it needs no containing MIMEMultipart section.

    :param attachments: A list of items to attach

    Items in ``attachments`` may have any of the following formats:

    - ``path`` of the file to attach
    - tuple of: ``(data_string, filename)``
    - tuple of: ``(fileob, filename)``
    - any mime object
    """
    if not attachments:
        return mime_body

    container = MIMEMultipart()
    container.attach(mime_body)
    for item in attachments:

        if isinstance(item, basestring):
            container.attach(attachment_from_file(item))
        elif isinstance(item, MIMEBase):
            container.attach(item)
        else:
            data, filename = item
            container.attach(attachment_from_string(data, filename))

    # Copy non-content specific headers from the original message to the new
    # container message (ie 'To', 'From', 'Subject' etc)
    for header in mime_body.keys():
        if header.lower().startswith('content'):
            continue
        for value in mime_body.get_all(header):
            container[header] = value
        del mime_body[header]

    return container


def attachment_from_file(path_or_file, filename=None):
    """
    Read from file at ``path`` and return a suitable MIME attachment object
    """
    if isinstance(path_or_file, basestring):
        with open(path_or_file, 'rb') as file_:
            return attachment_from_file(file_, filename)

    if filename is None:
        filename = os.path.basename(path_or_file.name)

    return attachment_from_string(path_or_file.read(), filename)


def attachment_from_string(data, filename, content_type=None):
    """
    Return a MIME attachment object for the data in bytestring ``data``.

    The attachment is given a ``Content-Disposition`` of ``attachment`` with
    ``filename`` specified as the filename.
    """

    if content_type is None:
        content_type, encoding = mimetypes.guess_type(filename)
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'

    maintype, subtype = content_type.split('/', 1)

    if maintype == 'text':
        attach = MIMEText(data, _subtype=subtype)

    elif maintype == 'message':
        attach = message_from_string(data)

    elif maintype == 'image':
        attach = MIMEImage(data, _subtype=subtype)

    elif maintype == 'audio':
        attach = MIMEAudio(data, _subtype=subtype)

    else:
        attach = MIMEBase(maintype, subtype)
        attach.set_payload(data)
        encode_base64(attach)

    attach.add_header('Content-Disposition', 'attachment', filename=filename)
    return attach


def split_headers(message_text):
    """
    Split headers from message body:

    >>> from mailtools.utils import split_headers
    >>> msg = "Subject: hi\\nTo: fred@example.org\\n\\r\\nHi there!"
    >>> split_headers(msg)
    ([('Subject', 'hi'), ('To', 'fred@example.org')], 'Hi there!')


    """

    linebreak = r"(?:\r\n|\r|\n)"
    header_field_name = r"[\x21-\x39\x3b-\x7e]+"
    header_separator = r":\x20"
    header_value = r"[^\r\n]*"
    header = header_field_name + header_separator + header_value + linebreak

    match = re.match(
        r'''
            (?P<headers>(?:''' + header + ''')*)
            (''' + linebreak + '''(?P<body>.*))?$
        ''',
        message_text,
        re.X | re.S
    )
    if match is None:
        return [], message_text

    headers = match.group('headers')
    body = match.group('body')

    headers = headers.strip()
    headers = headers and re.split(linebreak, headers) or []
    headers = [tuple(re.split(header_separator, h, 1)) for h in headers]
    headers = [(fieldname.encode('ascii'), value)
               for fieldname, value in headers]

    return headers, body


def make_header(value):
    """
    Return an ``email.header.Header`` object for unicode string ``value``, if
    ``value`` contains any non-ascii characters, otherwise return ``value``
    ascii encoded.
    """
    if isinstance(value, str):
        raise ValueError("Unicode value expected")
    try:
        return value.encode('ascii')
    except UnicodeEncodeError:
        return Header(value.encode('UTF-8'), 'UTF-8')


def extract_recipients(message):
    """
    Return a list of recipients from the given message's ``To``, ``Cc`` and
    ``Bcc`` fields, eg to be used in the envelope recipients.

    >>> from email.message import Message
    >>> from email.header import Header
    >>> from mailtools.utils import extract_recipients
    >>> m = Message()
    >>> m['To'] = Header('Olly <olly@example.com>, Molly <molly@example.com>',
    ...                  'utf8')
    >>> m['Cc'] = 'Holly <holly@example.com>'
    >>> m['Bcc'] = 'Polly <polly@example.com>'
    >>> extract_recipients(m)  # doctest: +NORMALIZE_WHITESPACE
    [u'olly@example.com', u'molly@example.com', u'holly@example.com',
     u'polly@example.com']
    """

    addresses = unicode(message.get('To', '')).split(',') \
            + unicode(message.get('Cc', '')).split(',') \
            + unicode(message.get('Bcc', '')).split(',')

    addresses = (s for s in addresses if s)
    addresses = (strip_name(s.strip()) for s in addresses)
    return list(addresses)


def strip_name(address):
    """
    >>> from mailtools.utils import strip_name
    >>> strip_name('Joe Bloggs <joe@example.org>')
    'joe@example.org'
    """
    match = re.match(r'.*<(.*)>$', address)
    if not match:
        return address
    return match.group(1)
