import Queue
import threading
from collections import namedtuple
from heapq import heappush, heappop
from time import time

from mailer import BaseMailer

__all__ = ['ThreadedMailer']

QueuedMessage = namedtuple('QueuedMessage', ['due', 'attempts', 'message'])

# Shutdown with a final delivery attempt
SHUTDOWN_SOFT = "SHUTDOWN_SOFT"

# Shutdown with no final delivery attempt
SHUTDOWN_HARD = "SHUTDOWN_HARD"


class ThreadedMailerClosedException(Exception):
    """
    Mailer has been closed and can no longer accept messages
    """


class ThreadedMailer(BaseMailer):
    """
    ``ThreadedMailer`` wraps a mailer to provide background sending of messages
    in a second thread and automatic retrying of temporary failures.

    Usage::

        >>> mailer = ThreadedMailer(SMTPMailer('127.0.0.1'))
        >>>
    """

    #: Send at most ``batch_size`` messages per SMTP session
    batch_size = 10

    #: How long to wait for new messages to appear before deciding to send a
    #: batch
    batch_sending_grace_period = 0.5

    #: retry unsendable messages for ``retry_period`` seconds
    retry_period = 600

    #: maximum number of attempts to deliver a message before discarding it
    max_attempts = 100

    #: maximum size of retry queue
    max_queue_size = 100

    #: how long to wait before timing out on shutdown
    shutdown_timeout = 30

    #: Whether to use daemon threads.
    #: If False, the python interpreter will not exit until the ThreadedMailer
    #: queue processor has terminated. Modify with care - this may cause your
    #: process to become hard to kill.
    _use_daemon_threads = True

    def __init__(self, mailer):
        """
        :param mailer: A ``Mailer`` instance that will be used to route
                       messages
        """
        super(ThreadedMailer, self).__init__()

        self.mailer = mailer

        # Queue of messages to be sent
        self.queue = Queue.Queue()

        # Internal priority queue of messages waiting for delivery
        # Items are tuples of ``(due_time, #attempts, message)``.
        self._to_process = []

        self.closed = threading.Event()
        self.queue_processor = threading.Thread(target=self.queue_processor)
        self.queue_processor.daemon = self._use_daemon_threads
        self.queue_processor.start()

    def send(self, envelope_sender, envelope_recipients, message):
        """
        Queue a single message for sending and return immediately

        ``envelope_sender``
            Envelope sender email address

        ``envelope_recipients``
            List of envelope recipient email addresses
        """
        if self.mailer.log_messages:
            self.mailer.logger.info(
                "Queuing message: \n\nFrom: %s\nTo: %s\n\n%s",
                envelope_sender, envelope_recipients, message
            )
        super(ThreadedMailer, self).send(
            envelope_sender,
            envelope_recipients,
            message,
        )

    def _send_many(self, messages):
        """
        Put ``messages`` into the queue.
        """
        if self.closed.is_set():
            raise ThreadedMailerClosedException()

        for message in messages:
            self.queue.put(message)

    def queue_processor(self):
        """
        Wait on the inbound queue for new items, wrap them up as QueuedMessages
        and push them on to self.requeue
        """

        # Open for business!
        self.closed.clear()

        while True:

            if self._to_process:
                timeout = max(0, self._to_process[0].due - time())
                timeout = timeout + self.batch_sending_grace_period
            else:
                timeout = None

            try:
                message = self.queue.get(timeout=timeout)
            except Queue.Empty:
                # No new messages have arrived within the specified timeout,
                # attempt delivery of all due messages and restart the loop
                self._process_due_messages()
                continue

            # Shutdown with final delivery attempt
            if message is SHUTDOWN_SOFT:
                self.closed.set()
                self.queue.task_done()
                self._process_due_messages(force=True)
                break

            # Shutdown with no final delivery attempt
            elif message is SHUTDOWN_HARD:
                self.closed.set()
                self.queue.task_done()
                for item in self._to_process:
                    self.queue.task_done()
                self._to_process = []
                break

            # Push all other messages gets onto the _to_process heap
            else:
                heappush(self._to_process,
                         QueuedMessage(0, 0, message))

    def _pop_due_messages(self):
        """
        Pop and return a list of due messages, up to a maximum of
        ``self.batch_size``.
        """
        due = []
        while (self._to_process and
               self._to_process[0].due < time() and
               len(due) < self.batch_size):
            due.append(heappop(self._to_process))
        return due

    def _process_due_messages(self, force=False):
        """
        Pop all due messages off the message pool and try to deliver them

        :param force: force delivery for all messages, ignoring due time
        """

        if not self._to_process:
            return

        if force:
            due = self._to_process[:]
            self._to_process = []
        else:
            due = self._pop_due_messages()

        self._deliver_messages(due, self._mark_done, self._mark_failed)

    def _mark_done(self, message):
        """
        Mark a single message as delivered
        """
        self.queue.task_done()

    def _mark_failed(self, exc_info, message):
        """
        Mark a single message as failed
        """
        if self.mailer.transport.is_retryable(exc_info[1]) and \
                message.attempts < self.max_attempts:
            heappush(self._to_process,
                     QueuedMessage(time() + self.retry_period,
                                   message.attempts + 1,
                                   message.message))

        else:
            # Drop the message
            self.queue.task_done()

    def _deliver_messages(self, messages, callback, error_callback):
        """
        :param messages: list of QueuedMessage tuples
        :param callback: callback to call once per delivered message
        :param error_callback: callback to call once per failed message
        """

        errors = self.mailer._send_many([m.message for m in messages])
        errors = dict((id(raw_message), error)
                      for error, raw_message in errors)

        for message in messages:
            raw_message = message.message
            if id(raw_message) in errors:
                error_callback(errors[id(raw_message)], message)
            else:
                callback(message)

    def shutdown_soft(self, timeout=600):
        return self.shutdown(timeout, SHUTDOWN_SOFT)

    def shutdown_hard(self, timeout=600):
        return self.shutdown(timeout, SHUTDOWN_HARD)

    def shutdown(self, timeout=600, signal=SHUTDOWN_SOFT):
        """
        Wait for the mailer to finish sending emails out.

        Return ``True`` if all emails were sent out before ``timeout``.
        """

        # Flag to clients we're no longer accepting messages
        self.closed.set()

        def timeout_left(start_time=time()):
            # How much timeout left to run?
            return max(0, timeout - (time() - start_time))

        # Tell the main queue to shutdown.
        # This should trigger immediate delivery attempts for all messages then
        # terminate the thread.
        if self.queue_processor.is_alive():
            self.queue.put(signal)
            self.queue_processor.join(timeout=timeout_left())

        thread_terminated = not self.queue_processor.is_alive()

        return (self.queue.unfinished_tasks == 0 and thread_terminated)
