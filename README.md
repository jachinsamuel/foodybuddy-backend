# FoodyBuddy — Backend

Server that powers the FoodyBuddy canteen ordering system. Built with Flask and PostgreSQL, deployed on Render.

---

## What This Does

The backend handles everything that happens behind the scenes — storing student accounts, processing payments, saving orders, sending WhatsApp messages, and serving menu data to the frontend. The frontend (student website) and Admin Panel both talk to this server.

---

## What Gets Stored

**Students**
- Name, WhatsApp number, hashed password, and role (student or admin)

**Menu Items**
- Name, price, category, veg/non-veg type, photo (stored on Cloudinary), and availability status

**Orders**
- Order ID, student name and phone, list of items ordered, total amount, payment method, order type (Dine-in / Takeaway), and current status

---

## Order Lifecycle

Every order goes through these stages, advanced manually by canteen staff from the Admin Panel:

```
New → Preparing → Ready → Done
```

- **New** — order just came in
- **Preparing** — canteen has started cooking
- **Ready** — food is ready, WhatsApp sent to student
- **Done** — student collected the food

---

## Payments

Two payment modes are supported:

**Online (Razorpay)**
Student pays via UPI, debit/credit card, or net banking. Razorpay processes the payment and the backend verifies it with a signature check before saving the order.

**Cash at Counter**
Order is saved immediately without any online payment. Student pays cash when they collect.

---

## WhatsApp Notifications (Twilio)

Three automatic messages are sent:

| Trigger | Recipient | Message |
|---|---|---|
| Order placed | Student | Order confirmed with ID and items |
| Order placed | Canteen number | New order alert with full details |
| Status set to Ready | Student | Your order is ready for pickup |

---

## Services Used

| Service | Purpose |
|---|---|
| PostgreSQL (Neon) | Stores all data — students, menu, orders |
| Razorpay | Processes online payments |
| Twilio | Sends WhatsApp notifications |
| Cloudinary | Stores food item photos uploaded from Admin Panel |
| Render | Hosts the backend server |

---

## Admin Actions Available

| Action | What happens |
|---|---|
| Advance order status | Updates order in DB, sends WhatsApp if status = Ready |
| Cancel order | Deletes order from DB |
| Clear history | Deletes all Done orders, resets daily revenue |
| Add menu item | Saves item + uploads photo to Cloudinary |
| Edit menu item | Updates item details or photo |
| Toggle availability | Shows/hides item from student menu without deleting |
| Delete menu item | Permanently removes item |

---

## Deployed At

Backend API running on Render — connected to the Vercel frontend.
