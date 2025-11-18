"""
app/routes/main.py
Main Routes
Handles homepage, about, contact pages, and general site navigation
"""

from flask import Blueprint, request, render_template, jsonify, url_for
from datetime import datetime

from app.models import Category, Product
from app.services import ProductService
from app.utils import StringHelper, ImageHelper
from app.database import health_check as db_health_check

# Create blueprint
main_bp = Blueprint('main', __name__)


# ============================================
# HOMEPAGE
# ============================================
@main_bp.route('/', methods=['GET'])  
def homepage():
    CATEGORY_ICON_MAP = {
        "mugs": "☕",
        "t-shirts": "👕",
        "bags": "👜",
        "tumblers": "🥤"
        # add more as needed
    }
    try:
        featured_products = ProductService.get_featured_products(limit=8)
        categories = ProductService.get_all_categories(include_inactive=False)
        popular_products = ProductService.get_popular_products(limit=6)

        # Attach correct image URLs using ImageHelper
        for p in featured_products:
            path = ImageHelper.get_product_image_url( p['product_id'], p.get('product_name'))
            p['image_url'] =  url_for('static', filename=path)

        for p in popular_products:
            path = ImageHelper.get_product_image_url( p['product_id'], p.get('product_name'))
            p['image_url'] =  url_for('static', filename=path)

        for c in categories:
            category_name_lower = c.get('category_name', '').lower()
            c['icon'] = CATEGORY_ICON_MAP.get(category_name_lower, "v")

        # About section
        about_info = {
            "company_name": "Custom Print Shop",
            "tagline": "Your Vision, Our Precision",
            "description": (
                "We provide high-quality custom printing services for all your needs. "
                "From personalized t-shirts to custom mugs, we bring your ideas to life."
            ),
            "services": [
                "Custom T-Shirt Printing",
                "Personalized Mugs & Drinkware",
                "Business Cards & Stationery",
                "Promotional Products",
                "Photo Printing & Canvas",
                "Custom Signage & Banners"
            ],
            "why_choose_us": [
                "High-quality printing technology",
                "Fast turnaround times",
                "Competitive pricing",
                "Expert design assistance",
                "100% satisfaction guarantee",
                "Eco-friendly printing options"
            ],
            "years_in_business": 10,
            "orders_completed": "50,000+"
        }

        return render_template(
            'homepage/index.html',
            featured_products=featured_products,
            categories=categories,
            popular_products=popular_products,
            about=about_info
        )

    except Exception as e:
        return render_template(
            'errors/error.html',
            error=f"Failed to load homepage: {e}"
        ), 500

# ============================================
# ABOUT PAGE
# ============================================
@main_bp.route('/about', methods=['GET'])
def about():
    """About page with company info"""
    about_info = {
        "company_name": "Custom Print Shop",
        "tagline": "Your Vision, Our Precision",
        "description": (
            "We provide high-quality custom printing services for all your needs. "
            "From personalized t-shirts to custom mugs, we bring your ideas to life."
        ),
        "services": [
            "Custom T-Shirt Printing",
            "Personalized Mugs & Drinkware",
            "Business Cards & Stationery",
            "Promotional Products",
            "Photo Printing & Canvas",
            "Custom Signage & Banners"
        ],
        "why_choose_us": [
            "High-quality printing technology",
            "Fast turnaround times",
            "Competitive pricing",
            "Expert design assistance",
            "100% satisfaction guarantee",
            "Eco-friendly printing options"
        ],
        "years_in_business": 10,
        "orders_completed": "50,000+"
    }
    return render_template('homepage/about.html', about=about_info)


# ============================================
# CONTACT PAGE
# ============================================
@main_bp.route('/contact', methods=['GET'])
def contact():
    """Contact page with info"""
    contact_info = {
        "email": "info@customprintshop.com",
        "phone": "+1 (555) 123-4567",
        "address": "123 Print Street, Design City, DC 12345",
        "business_hours": {
            "monday_friday": "9:00 AM - 6:00 PM",
            "saturday": "10:00 AM - 4:00 PM",
            "sunday": "Closed"
        },
        "social_media": {
            "facebook": "facebook.com/customprintshop",
            "instagram": "@customprintshop",
            "twitter": "@customprintshop"
        }
    }
    return render_template('homepage/contact.html', contact=contact_info)


# ============================================
# FEATURES PAGE
# ============================================
@main_bp.route('/features', methods=['GET'])
def features():
    """Features page"""
    features_list = [
        {"title": "Easy Design Upload", "description": "Upload designs in PNG, JPG, PDF, AI, SVG", "icon": "upload"},
        {"title": "Real-time Preview", "description": "Preview your design before ordering", "icon": "eye"},
        {"title": "Custom Text & Graphics", "description": "Add text, fonts, and colors easily", "icon": "edit"},
        {"title": "Bulk Ordering", "description": "Save with quantity discounts", "icon": "shopping-cart"},
        {"title": "Fast Production", "description": "Orders ship within 2-3 business days", "icon": "clock"},
        {"title": "Quality Guarantee", "description": "100% satisfaction or money back", "icon": "shield"},
    ]
    return render_template('homepage/features.html', features=features_list)


# ============================================
# FAQ PAGE
# ============================================
@main_bp.route('/faq', methods=['GET'])
def faq():
    """Frequently Asked Questions page"""
    return render_template('homepage/faq.html')


 
# ============================================
# TERMS OF SERVICE
# ============================================
@main_bp.route('/terms', methods=['GET'])
def terms():
    """Terms of service page"""
    terms_info = {
        "last_updated": "2025-01-01",
        "sections": [
            {"title": "Acceptance of Terms", "content": "By using our service, you agree to these terms."},
            {"title": "User Responsibilities", "content": "You must ensure uploaded content is yours or permitted."},
            {"title": "Copyright & IP", "content": "You must own or have rights to all submitted designs."},
            {"title": "Order Accuracy", "content": "We aren’t responsible for customer-submitted order errors."}
        ]
    }
    return render_template('homepage/terms.html', terms=terms_info)


# ============================================
# SEARCH (keeps JSON)
# ============================================
@main_bp.route('/search', methods=['GET'])
def search():
    """Search API endpoint"""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    limit = min(request.args.get('limit', 20, type=int), 100)

    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    if len(query) < 2:
        return jsonify({'error': 'Search query must be at least 2 characters'}), 400

    try:
        products = ProductService.search_products(query, category_id, limit)
        results = {
            'query': query,
            'count': len(products),
            'products': [
                {
                    'product_id': p['product_id'],
                    'product_name': p['product_name'],
                    'description': StringHelper.truncate_text(p.get('description'), 150),
                    'base_price': float(p['base_price']),
                    'slug': StringHelper.slugify(p['product_name'])
                } for p in products
            ]
        }
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': f'Search failed: {e}'}), 500


# ============================================
# SITEMAP (JSON only)
# ============================================
@main_bp.route('/sitemap', methods=['GET'])
def sitemap():
    """Site map endpoint"""
    return jsonify({
        "main": [
            {"name": "Home", "path": "/"},
            {"name": "About", "path": "/about"},
            {"name": "Contact", "path": "/contact"},
            {"name": "Features", "path": "/features"},
            {"name": "FAQ", "path": "/faq"}
        ],
        "products": [
            {"name": "All Products", "path": "/products"},
            {"name": "Categories", "path": "/products/categories"}
        ],
        "account": [
            {"name": "Login", "path": "/auth/login"},
            {"name": "Register", "path": "/auth/register"},
            {"name": "My Orders", "path": "/orders"},
            {"name": "Shopping Cart", "path": "/cart"}
        ],
        "legal": [ 
            {"name": "Terms of Service", "path": "/terms"}
        ]
    }), 200

 
# ============================================
# HEALTH CHECK (JSON only)
# ============================================
@main_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    
    try:
        db_health = db_health_check()
        health_status = {
            "status": "healthy" if db_health['status'] == 'healthy' else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_health['status'],
            "response_time_ms": db_health.get('response_time_ms')
        }
        return jsonify(health_status), (200 if health_status['status'] == 'healthy' else 503)
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


# ============================================
# ERROR HANDLERS
# ============================================
@main_bp.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500
