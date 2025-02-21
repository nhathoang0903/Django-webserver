import unittest
from PyQt5.QtWidgets import QApplication
from page5_qrcode import QRCodePage

class TestQRCodePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.page = QRCodePage()

    def test_cancel_payment(self):
        self.page.cancel_payment()
        self.assertTrue(self.page.stop_transaction_check.is_set(), "Transaction check should be stopped")
        self.assertFalse(self.page.countdown_timer.isActive(), "Countdown timer should be stopped")

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

if __name__ == '__main__':
    unittest.main()
