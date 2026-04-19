# FoodyBuddy Backend

A Flask-based REST API backend for FoodyBuddy, a college canteen food ordering system.

## What is FoodyBuddy?

FoodyBuddy is a web application that allows college students to browse and order food from the canteen. It provides a seamless ordering experience with real-time order tracking, favorites management, and admin controls for canteen staff.

## Key Features

- **User Authentication**: Secure login/signup with JWT authentication
- **Menu Management**: Browse food items organized by categories
- **Shopping Cart**: Add items to cart with optional add-ons
- **Favorites**: Save favorite items for quick access
- **Order Management**: Place orders with payment options
- **Order Tracking**: Real-time order status with visual indicators
- **Payment Integration**: Support for both Razorpay (online) and cash payments
- **Admin Dashboard**: Manage menu items, view orders, and control shop status
- **Shop Status Control**: Admin can open/close the shop to control orders

## How It Works

1. **User Authentication**: Students login with phone number and password
2. **Browse Menu**: View items by category, search, or filter by veg/non-veg
3. **Add Favorites**: Heart icon to save favorite items for quick ordering
4. **Customize Order**: Add optional add-ons and special instructions
5. **Checkout**: Select payment method (Razorpay or Cash)
6. **Track Order**: Real-time status updates as the order is prepared
7. **Admin Controls**: Staff can manage menu and update order status

## Tech Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL with JSONB support
- **Authentication**: JWT (JSON Web Tokens)
- **Payment Gateway**: Razorpay API
- **Server**: WSGI-compatible (Gunicorn)

### Frontend
- **Framework**: React 18
- **Styling**: CSS3 with CSS Variables
- **State Management**: React Hooks (useState, useContext)
- **API Client**: Fetch API
- **Payment**: Razorpay Payment Gateway

## Project Structure

### Backend (`foodybuddy-backend/`)
```
app.py                 # Flask application entry point
database.py            # PostgreSQL connection and initialization
auth_routes.py         # Login/signup endpoints
menu_routes.py         # Menu browsing endpoints
order_routes.py        # Order management endpoints
payment_routes.py      # Razorpay payment integration
favorites_routes.py    # Favorites system endpoints
admin_routes.py        # Admin dashboard endpoints
shop_status_routes.py  # Shop open/closed status
```

### Frontend (`foodybuddy-frontend/src/`)
```
components/
  ├── MenuScreen.js     # Browse menu with filters and search
  ├── CartScreen.js     # Shopping cart management
  ├── PaymentScreen.js  # Checkout and payment
  ├── OrderTracker.js   # Real-time order status
  ├── ProfileScreen.js  # User profile and order history
  ├── FavoritesScreen.js# Saved favorite items
  ├── AdminPanel.js     # Admin dashboard
  ├── BottomNav.js      # Navigation bar (Menu, Favorites, Orders, Cart, Profile)
  ├── AuthScreen.js     # Login/signup
  └── SkeletonLoader.js # Loading states
```

## Database Schema

### Users
- Stores user credentials and basic info
- Supports role-based access (user/admin)

### Menu Items
- Food items with prices, categories, and images
- Each item can have multiple add-ons

### Orders
- Order details with items, total price, payment status
- Stores order status (new → confirmed → preparing → ready → done)

### Favorites
- User-specific favorites list with unique constraints

### Shop Status
- Global shop status (open/closed)
- Controls whether orders can be placed

## API Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Menu
- `GET /menu` - Get all menu items
- `GET /addons/:item_id` - Get add-ons for item

### Shopping & Orders
- `POST /create-order` - Create Razorpay order
- `POST /place-cash-order` - Place cash order
- `GET /orders` - Get user's orders

### Favorites
- `GET /favorites?user_id=X` - Get user's favorites
- `POST /favorites/:item_id` - Add/remove favorite

### Admin
- `GET /admin/orders` - View all orders
- `POST /admin/orders/:order_id/status` - Update order status
- `GET /admin/menu` - View all menu items
- `POST /admin/menu` - Add new menu item
- `PUT /admin/menu/:item_id` - Edit menu item
- `DELETE /admin/menu/:item_id` - Delete menu item

### Shop Control
- `GET /shop-status` - Get current shop status
- `POST /shop-status` - Update shop status (admin only)

## Key Features in Detail

### Category Filtering
- Menu items organized by categories (Pizza, Burger, Sub, etc.)
- Each category shows item count
- Scrollable category bar for easy navigation

### Favorites System
- Heart icon to save favorite items
- Favorites persist across sessions
- Quick access from dedicated Favorites tab

### Order Tracking
- Visual progress indicator showing order status
- Token number generation for offline pickup
- Real-time updates on order progress

### Payment Options
- **Razorpay**: Online payment with credit/debit cards, UPI
- **Cash**: Cash on delivery with order confirmation

### Admin Dashboard
- View active and historical orders
- Manage menu (add/edit/delete items)
- Toggle shop open/closed status
- Real-time order management

### Responsive Design
- Mobile-first design optimized for phones
- Squircle navigation bar on desktop
- Full-width navigation on mobile
- Smooth animations and transitions

## Security Features

- JWT-based authentication for secure sessions
- Password hashing with bcrypt
- Role-based access control (admin/user)
- CORS configuration for API security
- Database validation and sanitization

## Performance Optimizations

- Skeleton loading states for smooth UX
- LocalStorage caching for menu data
- Lazy loading of images
- CSS animations using GPU acceleration
- Passive scroll listeners for smooth navigation
- Debounced search and filtering

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Order Status Flow

1. **New** - Order just placed
2. **Confirmed** - Order received by canteen staff
3. **Preparing** - Food is being prepared
4. **Ready** - Order is ready for pickup
5. **Done** - Order completed

## Payment Flow

### Razorpay
1. User selects items and checkout
2. Frontend creates order via backend
3. Razorpay payment modal opens
4. User completes payment
5. Order confirmed and added to queue

### Cash
1. User selects items and checkout
2. Shows order confirmation with token number
3. Order added to queue
4. User pays at counter during pickup

## Admin Features

- **Dashboard**: Overview of pending and completed orders
- **Live Orders**: Monitor active orders and update status
- **Menu Management**: Add/edit/delete menu items with images and add-ons
- **Order History**: View completed orders and revenue
- **Shop Status**: Toggle open/closed to control new orders
- **Settings**: Manage shop configuration

---

Built with ❤️ for Karunya Canteen

