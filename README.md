# PrintCraft - Custom Printing E-Commerce Platform

A full-featured custom printing e-commerce web application built with Flask and PostgreSQL. 
This platform allows customers to design and order custom-printed products like mugs, t-shirts, tumblers, and bags with personalized designs.

## 🌟 Features

### Customer Features
- **User Authentication**: Secure registration and login system with password validation
- **Guest Checkout**: Shop and checkout without creating an account
- **Product Browsing**: Browse products by category with filtering and sorting
- **Custom Design Upload**: Upload custom designs (PNG, JPG, GIF, etc.) for products
- **Design Preview**: Real-time preview of designs on product mockups
- **Shopping Cart**: Add, update, and remove items with persistent cart functionality
- **Order Management**: Place orders, track status, and view order history
- **Profile Management**: Update personal information and change password

### Admin Features
- **Admin Dashboard**: Overview of orders, revenue, customers, and products
- **Order Management**: View, update order status, and track order history
- **Product Management**: Create, update, deactivate, and delete products
- **Customer Management**: View customer details, orders, and manage accounts
- **User Management**: Create and manage admin accounts with role-based permissions
- **Activity Logging**: Track all administrative actions for audit purposes

### Technical Features
- **Role-Based Access Control**: Super Admin, Admin, and Staff roles with different permissions
- **Image Processing**: Automatic design overlay on product mockups
- **File Upload Management**: Secure file handling with validation
- **Session Management**: Persistent sessions for both guests and registered users
- **Responsive Design**: Mobile-friendly interface
- **Database Optimization**: Efficient queries with proper indexing
- **Security**: Password hashing, CSRF protection, input validation

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Database**: PostgreSQL with psycopg2
- **Image Processing**: Pillow (PIL)
- **Authentication**: Flask sessions with werkzeug security
- **Frontend**: HTML5, CSS3, JavaScript
- **Forms**: Flask-WTF with WTForms validation

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package installer)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/printcraft.git
cd printcraft
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=custom_print
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
DATABASE_SSLMODE=disable

# Application Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# File Upload
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# CORS (Optional)
CORS_ORIGINS=http://localhost:5000
```

### 5. Initialize Database
```bash
# Create database
createdb custom_print

# Run database schema
psql -U your_username -d custom_print -f database/01_schema.sql
psql -U your_username -d custom_print -f database/02_indexes.sql
psql -U your_username -d custom_print -f database/03_functions.sql
psql -U your_username -d custom_print -f database/04_triggers.sql
psql -U your_username -d custom_print -f database/05_views.sql
psql -U your_username -d custom_print -f database/06_inserts.sql
```

Or use the Flask CLI:
```bash
flask init-database
```

### 6. Create Required Directories
```bash
mkdir -p app/static/images/products/mockups
mkdir -p app/static/images/designs
mkdir -p app/static/images/previews
```

### 7. Run the Application
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## 📁 Project Structure
```
CUSTOM-PRINT-SHOP/
├── app/
│   ├── models/              # Database models
│   ├── routes/              # Flask blueprints/routes
│   ├── services/            # Business logic layer
│   ├── static/              # CSS, JS, images
│   ├── templates/           # Jinja2 templates
│   ├── utils/               # Helper functions
│   ├── config.py            # Configuration classes
│   ├── database.py          # Database connection
│   └── __init__.py          # Flask app factory
├── database/                # SQL schema and migrations
├── requirements.txt         # Python dependencies
└── run.py                   # Application entry point
```

## 🔑 Default Admin Account

After running the database inserts, you can login with:
- **Email**: admin@printcraft.com
- **Password**: admin123 (change immediately in production)

## 📚 API Endpoints

### Public Routes
- `GET /` - Homepage
- `GET /products/list` - Product listing
- `GET /products/<id>` - Product design page
- `GET /cart/view` - View shopping cart
- `POST /cart/add` - Add item to cart

### Customer Routes (Authentication Required)
- `GET /customer/profile` - View profile
- `GET /orders/list` - Order history
- `GET /orders/<id>` - Order details
- `POST /orders/checkout` - Place order

### Admin Routes (Admin Authentication Required)
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/orders` - Manage orders
- `GET /admin/products` - Manage products
- `GET /admin/customers` - Manage customers
- `POST /admin/orders/<id>/status` - Update order status

## 🎨 Customization

### Adding New Products
1. Login as admin
2. Navigate to Products Management
3. Fill in product details and upload image
4. Product mockup should be placed in `static/images/products/mockups/`

### Modifying Email Templates
Email templates are located in `templates/emails/` (if implemented)

### Styling
Main CSS files are in `app/static/css/`:
- `base.css` - Global styles
- `admin_base.css` - Admin panel styles
- `products.css` - Product pages
- `cart-order.css` - Cart and checkout

## 🔒 Security Features

- **Password Hashing**: Using werkzeug.security
- **Input Validation**: Server-side validation for all forms
- **SQL Injection Prevention**: Parameterized queries with psycopg2
- **CSRF Protection**: Flask-WTF CSRF tokens
- **Session Security**: Secure cookie settings
- **File Upload Validation**: File type and size restrictions
- **Role-Based Access**: Permission decorators for routes

## 🧪 Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=app tests/
```

## 📦 Deployment

### Production Checklist
1. Set `FLASK_ENV=production` in `.env`
2. Use strong `SECRET_KEY`
3. Enable SSL/TLS (set `SESSION_COOKIE_SECURE=True`)
4. Set up proper database backups
5. Configure reverse proxy (nginx/Apache)
6. Use production WSGI server (Gunicorn/uWSGI)
7. Set up monitoring and logging
8. Configure file upload limits
9. Enable database connection pooling

### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 'app:app'
```

### Using Docker
```bash
docker build -t printcraft .
docker run -p 5000:5000 printcraft
```

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database exists
psql -l

# Test connection
psql -U your_username -d custom_print -c "SELECT 1"
```

### Image Upload Issues
- Verify `UPLOAD_FOLDER` exists and has write permissions
- Check `MAX_CONTENT_LENGTH` setting in config
- Ensure PIL/Pillow is properly installed

### Session Issues
- Clear browser cookies
- Verify `SECRET_KEY` is set
- Check session configuration in `config.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Melissa Bangloy* - *Initial work*

## 🙏 Acknowledgments

- Flask documentation
- PostgreSQL community
- Bootstrap/CSS frameworks 

 
## 🗺️ Roadmap

- [ ] Payment gateway integration (Stripe/PayPal)
- [ ] Email notifications for orders
- [ ] Advanced design editor
- [ ] Bulk order discounts
- [ ] Wishlist functionality
- [ ] Product reviews and ratings
- [ ] Social media integration
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] Mobile app

## 📊 Database Schema

The application uses a normalized PostgreSQL database with the following main tables:

- **customers** - Customer accounts
- **admin_users** - Admin accounts with roles
- **categories** - Product categories
- **products** - Available products
- **shopping_carts** - Active shopping carts
- **cart_items** - Items in carts
- **orders** - Placed orders
- **order_items** - Items in orders
- **uploaded_files** - Customer design files
- **order_status_history** - Order status tracking
- **admin_activity_log** - Audit trail

See `database/01_schema.sql` for complete schema.

---

