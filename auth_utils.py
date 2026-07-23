import secrets
import string
import smtplib
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. SECURE PASSWORD HASHING ---
def hash_password(password: str) -> str:
    """Hashes a password using bcrypt for secure database storage."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Decode back to string so Supabase can store it

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if a plain text password matches the hashed version."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# --- 2. CRYPTOGRAPHIC OTP GENERATION ---
def generate_otp(length=6) -> str:
    """Generates a cryptographically secure n-digit OTP."""
    alphabet = string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# --- 3. GMAIL SMTP DELIVERY ---
def send_otp_email(recipient_email: str, otp_code: str):
    """Sends the OTP to the user using your working Gmail App Password."""
    # TODO: Replace these with your actual credentials (or use environment variables)
    sender_email = "abhijithbiju485@gmail.com" 
    app_password = "kfafdppzjsyqqbmk" 
    
    msg = MIMEMultipart()
    msg['From'] = f"Project Veda <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = "Your Project Veda Verification Code"
    
    body = f"Welcome to Project Veda!\n\nYour 6-digit secure verification code is: {otp_code}\n\nThis code is valid for 10 minutes. Please do not share it with anyone."
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email delivery failed: {e}")
        return False