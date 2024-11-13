import unittest
import email.utils
from pytlsrpt import tlsrpt

class MyTestCase(unittest.TestCase):
    def test_email_headers(self):
        """
        Test if setting of email headers needed for a TLSRPT report works
        :return:
        """
        msg = tlsrpt.EmailReport()
        #msg['Subject'] = self.create_email_subject(dom, self.report_id(day, uniqid, dom))
        msg['From'] = "sender@s.example.com"
        msg['To'] = "recipient@r.example.com"
        message_id = email.utils.make_msgid(domain=msg["From"].groups[0].addresses[0].domain)
        msg.add_header("Message-ID", message_id)
        msg.add_header("TLS-Report-Domain", "example.com")
        msg.add_header("TLS-Report-Submitter", "Example Inc")

        self.assertEqual(msg.get_header("Message-ID"), message_id)
        self.assertEqual(msg.get_header("TLS-Report-Domain"), "example.com")
        self.assertEqual(msg.get_header("TLS-Report-Submitter"), "Example Inc")


if __name__ == '__main__':
    unittest.main()
