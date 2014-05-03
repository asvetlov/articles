from datetime import datetime, timedelta


class Billing(object):
    now = datetime.now

    def __init__(self):
        self.timestamp = self.now()

    def can_show(self):
        return self.now() - self.timestamp < timedelta(seconds=5)




#### Test
import unittest
import mocker


class TestBillling(unittest.TestCase):
    def setUp(self):
        self.mocker = mocker.Mocker()

    def tearDown(self):
        self.mocker = None

    def test_can_show(self):
        billing = Billing()
        now = self.mocker.mock()

        stamp = billing.timestamp

        billing.now = now

        # mocker setup
        with self.mocker.order():
            # first call - just now
            now()
            self.mocker.result(stamp)

            # after 4 seconds
            now()
            self.mocker.result(stamp + timedelta(seconds=4))

            # after next 4 seconds
            now()
            self.mocker.result(stamp + timedelta(seconds=8))

        # test replay
        with self.mocker:
            # first call
            self.assertEqual(True, billing.can_show())
            # second call
            self.assertEqual(True, billing.can_show())
            # third call
            self.assertEqual(False, billing.can_show())


unittest.main()
