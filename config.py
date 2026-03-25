import os, razorpay, cloudinary
from twilio.rest import Client as TwilioClient

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

razorpay_client = razorpay.Client(auth=(
    os.environ.get("RAZORPAY_KEY_ID"),
    os.environ.get("RAZORPAY_KEY_SECRET")
))

twilio_client  = TwilioClient(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
TWILIO_NUMBER = "whatsapp:+14155238886"
CANTEEN_NUMBER = "whatsapp:+919944001925"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "canteen@admin123")
