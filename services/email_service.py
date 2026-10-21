import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage 
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD")

async def send_real_otp_email(receiver_email: str, otp_code: str):
    try:
        # Create the email content
        message = MIMEMultipart("related") # 'related' is important for embedded images
        message["From"] = f"DocuMind Security <{SENDER_EMAIL}>"
        message["To"] = receiver_email
        message["Subject"] = "Your DocuMind Verification Code"

        # HTML with CID for the logo
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #F8F9FA;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                
                <!-- HEADER WITH EMBEDDED LOGO -->
                <tr>
                    <td align="center" style="padding: 40px 0 20px 0; background-color: #ffffff;">
                        <!-- 🚀 The 'cid' MUST exactly match the Content-ID string without the <> brackets -->
                        <img src="cid:Logo.png" alt="DocuMind Logo" width="60" style="display: block; margin-bottom: 10px;" />
                        <h1 style="color: #0056D2; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px;">DocuMind</h1>
                    </td>
                </tr>

                <!-- MAIN CONTENT -->
                <tr>
                    <td style="padding: 20px 40px; text-align: center;">
                        <h2 style="color: #1E293B; margin: 0 0 15px 0; font-size: 20px; font-weight: bold;">Security Setup</h2>
                        <p style="color: #64748B; font-size: 15px; line-height: 1.6; margin: 0 0 30px 0;">
                            You requested to link this email to your DocuMind account. Use the verification code below to complete your setup.
                        </p>
                        
                        <!-- OTP BOX -->
                        <div style="background-color: #F1F5F9; border-radius: 8px; padding: 25px; margin: 0 auto; display: inline-block; border: 1px solid #E2E8F0;">
                            <h1 style="color: #0F172A; margin: 0; font-size: 36px; letter-spacing: 12px; font-weight: bold; text-align: center;">
                                {otp_code}
                            </h1>
                        </div>
                        
                        <p style="color: #EF4444; font-size: 13px; font-weight: bold; margin: 30px 0 0 0;">
                            This code will expire in 10 minutes.
                        </p>
                    </td>
                </tr>

                <!-- FOOTER -->
                <tr>
                    <td style="background-color: #F8FAFC; padding: 30px 40px; text-align: center; border-top: 1px solid #F1F5F9;">
                        <p style="color: #94A3B8; font-size: 12px; line-height: 1.5; margin: 0;">
                            If you didn't request this code, you can safely ignore this email.<br>
                            Your account remains secure.
                        </p>
                        <p style="color: #CBD5E1; font-size: 12px; margin: 15px 0 0 0;">
                            &copy; 2026 DocuMind-AI System. All rights reserved.
                        </p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Attach HTML part
        msg_alternative = MIMEMultipart('alternative')
        message.attach(msg_alternative)
        msg_alternative.attach(MIMEText(html_body, "html"))

        # 🚀 ATTACH LOCAL IMAGE AS CID (FIXED) 🚀
        try:
            
            logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png") 
            
            with open(logo_path, 'rb') as img_file:
                logo_img = MIMEImage(img_file.read())
                
               
                logo_img.add_header('Content-ID', '<Logo.png>')
                
               
                logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
                
                message.attach(logo_img)
        except Exception as img_err:
            print("Warning: Logo image not found or couldn't be attached.", img_err)

        # Connect to Gmail Server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls() # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Send Email
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        server.quit()

        return True, "Email sent successfully"
    except Exception as e:
        print("Email sending failed:", e)
        return False, str(e)