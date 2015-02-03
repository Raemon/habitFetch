import os

from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tempfile import NamedTemporaryFile

from nose.tools import assert_equal

from mailtools.utils import attachment_from_file
from mailtools.utils import attachment_from_string

def test_attachment_from_string_returns_correct_MIME_class_and_sets_correct_content_type():

    for fname, expected_class, expected_content_type in [
        ('a.txt', MIMEText, 'text/plain; charset="us-ascii"'),
        ('a.eml', Message, None),
        ('a.png', MIMEImage, 'image/png'),
        ('a.mp3', MIMEAudio, 'audio/mpeg'),
        ('a.unknown', MIMEBase, 'application/octet-stream'),
    ]:
        result = attachment_from_string('hello', fname)
        assert isinstance(result, expected_class), "Expected %r, got %r" % (expected_class, result)
        assert_equal(result['Content-Type'], expected_content_type)


def test_attachment_from_file_reads_content():

    with NamedTemporaryFile(suffix='.txt') as tmp:

            tmp.write('hello world')
            tmp.flush()

            result = attachment_from_file(tmp.name)
            assert_equal(result.get_payload(), 'hello world')

            with open(tmp.name) as tmp2:
                result = attachment_from_file(tmp2)
                assert_equal(result.get_payload(), 'hello world')


def test_attachment_from_file_sets_content_type_from_filename():

    for suffix, expected_class, expected_content_type in [
        ('.txt', MIMEText, 'text/plain; charset="us-ascii"'),
        ('.eml', Message, None),
        ('.png', MIMEImage, 'image/png'),
        ('.mp3', MIMEAudio, 'audio/mpeg'),
        ('.unknown', MIMEBase, 'application/octet-stream'),
    ]:
        with NamedTemporaryFile(suffix=suffix) as tmp:

            result = attachment_from_file(tmp.name)
            assert isinstance(result, expected_class), "Expected %r, got %r" % (expected_class, result)
            assert_equal(result['Content-Type'], expected_content_type)

            result = attachment_from_file(tmp)
            assert isinstance(result, expected_class), "Expected %r, got %r" % (expected_class, result)
            assert_equal(result['Content-Type'], expected_content_type)

def test_attachment_from_file_sets_filename():

    with NamedTemporaryFile(suffix='.txt') as tmp:

            tmp.write('hello world')
            tmp.flush()

            result = attachment_from_file(tmp)
            assert_equal(result['Content-Disposition'], 'attachment; filename="%s"' % os.path.basename(tmp.name))

            result = attachment_from_file(tmp.name)
            assert_equal(result['Content-Disposition'], 'attachment; filename="%s"' % os.path.basename(tmp.name))


def test_attachment_from_file_allows_filename_to_be_overridden():

    with NamedTemporaryFile(suffix='.txt') as tmp:

            tmp.write('hello world')
            tmp.flush()

            result = attachment_from_file(tmp, 'foo.png')
            assert_equal(result['Content-Disposition'], 'attachment; filename="foo.png"')

            result = attachment_from_file(tmp.name, 'foo.png')
            assert_equal(result['Content-Disposition'], 'attachment; filename="foo.png"')


