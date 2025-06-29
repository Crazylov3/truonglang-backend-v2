import secrets
import string
import traceback
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        if settings.sendgrid_api_key:
            self.sg = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        else:
            self.sg = None
            logger.warning("SendGrid API key not configured. Email services will not work.")

    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP."""
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email using SendGrid."""
        if not self.sg:
            logger.error("SendGrid not configured. Cannot send email.")
            return False

        try:
            message = Mail(
                from_email=(settings.from_email, settings.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.sg.send(message)
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def send_verification_email(self, to_email: str, otp: str) -> bool:
        """Send email verification OTP."""
        subject = "Verify your email - Giao Duc Thang Long"
        html_content = f"""
        <html>
        <body>
        <h2>Welcome to Giao Duc Thang Long!</h2>
        <p>Thank you for registering with us. Please use the following OTP to verify your email address:</p>
        <h3 style="color: #4CAF50; font-size: 24px; text-align: center; padding: 20px; background-color: #f5f5f5; border-radius: 5px;">
        {otp}
        </h3>
        <p>This OTP is valid for {settings.otp_expire_minutes} minutes.</p>
        <p>If you didn't request this verification, please ignore this email.</p>
        <br>
        <p>Best regards,<br>The Learnify Team</p>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html_content)

    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email with complex token (legacy method)."""
        # In a real application, you would include a link to your frontend
        # For now, we'll just send the token
        subject = "Password Reset - Giao Duc Thang Long"
        html_content = f"""
        <html>
        <body>
        <h2>Password Reset Request</h2>
        <p>You have requested to reset your password for your Giao Duc Thang Long account.</p>
        <p>Please use the following token to reset your password:</p>
        <p style="color: #4CAF50; font-size: 18px; font-weight: bold; padding: 10px; background-color: #f5f5f5; border-radius: 5px;">
        {reset_token}
        </p>
        <p>This token is valid for {settings.password_reset_expire_minutes} minutes.</p>
        <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
        <br>
        <p>Best regards,<br>The Learnify Team</p>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html_content)

    async def send_password_reset_otp_email(self, to_email: str, otp: str) -> bool:
        """Send password reset email with simple OTP."""
        subject = "Password Reset OTP - Giao Duc Thang Long"
        html_content = f"""
        <html>
        <body>
        <h2>Password Reset Request</h2>
        <p>You have requested to reset your password for your Giao Duc Thang Long account.</p>
        <p>Please use the following OTP to reset your password:</p>
        <h3 style="color: #4CAF50; font-size: 32px; text-align: center; padding: 20px; background-color: #f5f5f5; border-radius: 5px; letter-spacing: 8px;">
        {otp}
        </h3>
        <p><strong>This OTP is valid for {settings.otp_expire_minutes} minutes.</strong></p>
        <p style="color: #666; font-size: 14px;">
        Simply enter this 6-digit code in the password reset form. Much easier than copying long tokens!
        </p>
        <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
        <br>
        <p>Best regards,<br>The Learnify Team</p>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html_content)

    async def send_welcome_email(self, to_email: str, full_name: str) -> bool:
        """Send welcome email after successful verification."""
        subject = "Welcome to Giao Duc Thang Long!"
        html_content = f"""
        <html>
        <body>
        <h2>Welcome to Giao Duc Thang Long, {full_name}!</h2>
        <p>Your email has been successfully verified and your account is now active.</p>
        <p>You can now:</p>
        <ul>
        <li>Browse and enroll in courses</li>
        <li>Access your learning dashboard</li>
        <li>Track your progress</li>
        </ul>
        <p>Thank you for joining our learning community!</p>
        <br>
        <p>Best regards,<br>The Learnify Team</p>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html_content)


# Global email service instance
email_service = EmailService() 