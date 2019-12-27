import smtplib
import ssl


class EmailSender:
    receiver_email = ""
    email_subject = ""

    def __init__(self, receiver_email):
        self.receiver_email = receiver_email

    def send_email(self, email_content, email_subject):
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        sender_email = "your.email@gmail.com"  # Enter your address
        receiver_email = self.receiver_email  # Enter receiver address
        password = '*******'
        message = 'Subject: {}\n\n{}'.format(email_subject, email_content.encode("ascii", errors="ignore"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
