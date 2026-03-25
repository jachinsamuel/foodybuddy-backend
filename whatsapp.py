from config import twilio_client, TWILIO_NUMBER, CANTEEN_NUMBER

def _send_wa_customer(data):
    items="\n".join([f"  {i['name']} x{i['qty']} — ₹{i['price']*i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=f"Hi {data['name']}! Your order is confirmed.\n\nOrder: {data['razorpay_order_id']}\n{items}\n\nTotal: ₹{data['total']}\nType: {token_type.title()}\n\nWe'll notify you when it's ready.",
        from_=TWILIO_NUMBER, to=f"whatsapp:+91{data['phone']}")

def _send_wa_canteen(data):
    items="\n".join([f"  {i['name']} x{i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=f"New Order\nID: {data['razorpay_order_id']}\nFrom: {data['name']} ({token_type.title()})\n{items}\nTotal: ₹{data['total']}",
        from_=TWILIO_NUMBER, to=CANTEEN_NUMBER)

def _send_wa_ready(phone, order_id, token_type):
    twilio_client.messages.create(
        body=f"Your order is ready for collection!\n\nOrder: {order_id}\nType: {token_type.title()}\n\nPlease collect from the counter.",
        from_=TWILIO_NUMBER, to=f"whatsapp:+91{phone}")
