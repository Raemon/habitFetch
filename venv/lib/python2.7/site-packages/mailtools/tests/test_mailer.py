"""
Test suite for mailtools.mailer
"""

import sys
import logging
import Queue
import time

from email import message_from_string
from smtplib import SMTPResponseException

from nose.tools import assert_equal, assert_raises

from mailtools.mailer import SMTPTransport
from mailtools.mailer import Mailer
from mailtools.threadedmailer import ThreadedMailer,\
                                     ThreadedMailerClosedException


class CallbackHandler(logging.Handler):
    """
    Handler that allows a test case to intercept messages logged by the mailer
    object
    """

    def __init__(self,
                 callback=None,
                 debug_callback=None,
                 info_callback=None,
                 warn_callback=None,
                 error_callback=None,
                 critical_callback=None,
        ):

        """
        Initialize the Handler. If ``callback`` is set, it will be called with
        all records logged. If any of the other ``*_callback`` arguments are
        given, those callbacks will be triggered on reciept of a log record of
        exactly that level.
        """
        logging.Handler.__init__(self)
        self.callback = callback
        self.level_callbacks = {
            logging.DEBUG: debug_callback,
            logging.INFO: info_callback,
            logging.WARNING: warn_callback,
            logging.ERROR: error_callback,
            logging.CRITICAL: critical_callback,
        }

    def emit(self, record):
        """
        Implementation of ``logging.Handler.emit``
        """
        if self.callback is not None:
            self.callback(record)
        cb = self.level_callbacks[record.levelno]
        if cb is not None:
            cb(record)


class MockTransport(SMTPTransport):

    def __init__(self, *args, **kwargs):
        super(MockTransport, self).__init__('127.0.0.1')
        self.sent = Queue.Queue()
        self.sent_batches = Queue.Queue()
        self.log = []
        self.debug_log = []
        self.info_log = []
        self.warning_log = []
        self.error_log = []
        self.critical_log = []
        self.called_at = []
        self.callback = lambda msg: None

        self.logger = logging.getLogger('%d-0x%x' % (time.time(), id(self)))
        self.logger.addHandler(CallbackHandler(
            callback=self.log.append,
            debug_callback=self.debug_log.append,
            info_callback=self.info_log.append,
            warn_callback=self.warning_log.append,
            error_callback=self.error_log.append,
            critical_callback=self.critical_log.append,
        ))

    def send_many(self, messages):
        self.called_at.append(time.time())
        self.sent_batches.put(messages)
        for m in messages:
            self.sent.put(m)
            self.callback(m)
        return []


class MockTransportWithError(MockTransport):
    """
    Will return a 500 delivery failure message when called
    """
    error_args = (500, 'permanent failure')

    def send_many(self, messages):
        self.called_at.append(time.time())
        try:
            raise SMTPResponseException(*self.error_args)
        except Exception:
            exc_info = sys.exc_info()
            return [(exc_info, message) for message in messages]


class MockTransportWithRetry(MockTransportWithError):

    error_args = (400, 'temporary failure')


class MockTransportWithRetryOnce(MockTransportWithRetry):
    def send_many(self, messages):
        if len(self.called_at) < 1:
            return super(MockTransportWithRetryOnce, self).send_many(messages)
        else:
            return MockTransport.send_many(self, messages)


def test_sending_many_messages_returns_errors():

    transport = MockTransportWithError()
    mailer = Mailer(transport=transport, logger=transport.logger)
    mailer._send_many([('fromaddr', ['toaddr'], 'message')])

    exc_info = transport.error_log[0].args[0]
    assert "permanent failure" in str(exc_info[1])


class TestThreadedMailer(object):

    def test_it_sends_a_message(self):

        transport = MockTransport()
        mailer = ThreadedMailer(Mailer(transport=transport))
        message = ('fromaddr', ['toaddr'], 'message')
        mailer.send(*message)
        assert_equal(message, transport.sent.get(timeout=1))

    def test_it_retries_a_temporary_failure_at_correct_interval(self):

        transport = MockTransportWithRetryOnce()
        mailer = ThreadedMailer(Mailer(transport=transport,
                                    logger=transport.logger))
        mailer.retry_period = 0.2
        mailer.batch_sending_grace_period = 0

        message = ('fromaddr', ['toaddr'], 'message')
        mailer.send(*message)
        assert_equal(message, transport.sent.get(timeout=2))

        assert len(transport.called_at) == 2, \
                "transport was not called exactly twice"
        assert transport.called_at[1] - transport.called_at[0] >= \
                mailer.retry_period, "retried too soon"

        exc_info = transport.error_log[0].args[0]
        assert "temporary failure" in str(exc_info[1]),\
                "initial failure not logged"

        assert mailer.queue.empty()
        assert len(mailer._to_process) == 0

    def test_it_doesnt_retry_a_permanent_failure(self):

        transport = MockTransportWithError()
        mailer = ThreadedMailer(Mailer(transport=transport,
                                    logger=transport.logger))
        mailer.retry_period = 0.1

        message = ('fromaddr', ['toaddr'], 'message')
        mailer.send(*message)
        try:
            transport.sent.get(timeout=1)
        except Queue.Empty:
            pass
        else:
            raise AssertionError("Message should not have been sent")

        assert len(transport.called_at) == 1, \
                "transport was not called exactly once"

    def test_it_responds_to_new_items_on_queue(self):

        transport = MockTransportWithError()
        mailer = ThreadedMailer(Mailer(transport=transport))
        # Don't batch messages together
        mailer.batch_sending_grace_period = 0

        mailer.retry_period = 100
        message1 = ('fromaddr', ['toaddr'], 'message1')
        message2 = ('fromaddr', ['toaddr'], 'message2')

        # First message processed without delay?
        mailer.send(*message1)
        time.sleep(0.1)
        assert len(transport.called_at) == 1

        # Subsequent message also processed without delay?
        mailer.send(*message2)
        time.sleep(0.1)
        assert len(transport.called_at) == 2

        mailer.shutdown_hard()

    def test_it_sends_multiple_messages(self):

        transport = MockTransport()
        mailer = ThreadedMailer(Mailer(transport=transport,
                                    logger=transport.logger))

        messages = [
            ('fromaddr', ['toaddr'], 'message-%d' % ix)
            for ix in range(20)
        ]
        expected = set('message-%d' % ix for ix in range(20))

        for m in messages:
            mailer.send(*m)
        while expected:
            try:
                fromaddr, toaddrs, message = transport.sent.get(timeout=2)
                expected.remove(message)
            except Queue.Empty:
                raise AssertionError("Message expected")

    def test_it_sends_in_time_limited_batches(self):

        transport = MockTransport()
        mailer = ThreadedMailer(Mailer(transport=transport,
                                    logger=transport.logger))
        mailer.batch_size = 10
        mailer.batch_sending_grace_period = 0.1

        messages = [
            ('fromaddr', ['toaddr'], 'm1'),
            ('fromaddr', ['toaddr'], 'm2'),
            ('fromaddr', ['toaddr'], 'm3'),
            ('fromaddr', ['toaddr'], 'm4'),
            ('fromaddr', ['toaddr'], 'm5'),
        ]

        mailer.send(*messages[0])
        mailer.send(*messages[1])
        time.sleep(mailer.batch_sending_grace_period * 1.5)
        mailer.send(*messages[2])
        mailer.send(*messages[3])
        time.sleep(mailer.batch_sending_grace_period * 1.5)
        mailer.send(*messages[4])

        assert transport.sent_batches.get() == [messages[0], messages[1]]
        assert transport.sent_batches.get() == [messages[2], messages[3]]
        assert transport.sent_batches.get() == [messages[4]]
        assert transport.sent_batches.empty()

    def test_it_sends_in_size_limited_batches(self):

        transport = MockTransport()
        mailer = ThreadedMailer(Mailer(transport=transport,
                                    logger=transport.logger))
        mailer.batch_size = 2
        mailer.batch_sending_grace_period = 0.2

        messages = [
            ('fromaddr', ['toaddr'], 'm1'),
            ('fromaddr', ['toaddr'], 'm2'),
            ('fromaddr', ['toaddr'], 'm3'),
            ('fromaddr', ['toaddr'], 'm4'),
            ('fromaddr', ['toaddr'], 'm5'),
        ]

        for m in messages:
            mailer.send(*m)

        assert transport.sent_batches.get() == [messages[0], messages[1]]
        assert transport.sent_batches.get() == [messages[2], messages[3]]
        assert transport.sent_batches.get() == [messages[4]]
        assert transport.sent_batches.empty()


def test_send_plain_sets_text_plain_content_type():

    transport = MockTransport()
    mailer = Mailer(transport=transport)
    mailer.send_plain(u'me@mydomain', [u'you@yourdomain'],
                      u'subject line', u'Hi buddy!')
    env_from, env_to, message = transport.sent.get()

    assert_equal(message_from_string(message)['Content-Type'],
                 'text/plain; charset=UTF-8')


def test_send_html_sets_text_html_content_type():

    transport = MockTransport()
    mailer = Mailer(transport=transport)
    mailer.send_html(u'me@mydomain', [u'you@yourdomain'],
                     u'subject line', u'Hi buddy!')
    env_from, env_to, message = transport.sent.get()

    assert_equal(message_from_string(message)['Content-Type'],
                 'text/html; charset=UTF-8')


class TestThreadedMailerShutdown(object):

    def test_it_returns_true_when_no_messages_are_queued(self):
        t = ThreadedMailer(Mailer(transport=MockTransport()))
        assert t.shutdown() is True

    def test_it_returns_false_when_retries_are_pending(self):
        t = ThreadedMailer(Mailer(transport=MockTransportWithRetry()))
        t.send('fromaddr', ['toaddr'], 'message')
        assert t.shutdown(timeout=0.5) is False

    def test_it_throws_an_exception_queueing_messages_after_shutdown(self):
        t = ThreadedMailer(Mailer(transport=MockTransport()))
        t.shutdown()
        assert_raises(ThreadedMailerClosedException,
                      t.send, 'fromaddr', ['toaddr'], 'message')

    def test_it_can_send_mails_from_beyond_the_grave(self):

        from tempfile import NamedTemporaryFile
        from subprocess import check_output

        with NamedTemporaryFile() as tmp:
            tmp.write("""
import atexit
import sys
sys.path = {sys_path}
from mailtools import ThreadedMailer, Mailer
from mailtools.tests.test_mailer import MockTransport

def callback(message):
    sys.stdout.write('message sent: %r' % (message,))
    sys.stdout.flush()

transport = MockTransport()
transport.callback = callback

t = ThreadedMailer(Mailer(transport=transport))
# Set a long batch sending grace period to delay message sending until
# interpreter shutdown
t.batch_sending_grace_period = 10

atexit.register(t.shutdown_soft)

t.send('fromaddr', ['toaddr'], 'message')
assert transport.called_at == []
            """.format(sys_path=sys.path))

            tmp.flush()
            output = check_output([sys.executable, tmp.name]).strip()
            assert output == \
                "message sent: ('fromaddr', ['toaddr'], 'message')", \
                repr(output)
