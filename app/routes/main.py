"""
app/routes/main.py
Main Routes
Handles homepage, about, contact pages, and general site navigation
"""

# TODO: use render_template for html
# TODO: remove JSONify 

from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime
 

from app.models import Category, Product
from app.services import ProductService
from app.utils import StringHelper, Validators

# Create blueprint
main_bp = Blueprint('main', __name__)


# ============================================
# HOMEPAGE
# ============================================
"""
    GET /
    Homepage with featured products and categories

    Returns:
        HTML page or JSON depending on request type
"""
@main_bp.route('/', methods=['GET'])
def homepage(): 
    try:
        # Get featured/newest products
        featured_products = ProductService.get_featured_products(limit=8)
        
        # Get all active categories
        categories = ProductService.get_all_categories(include_inactive=False)
        
        # Get popular products (most ordered)
        popular_products = ProductService.get_popular_products(limit=6)
        
        # Check if JSON response is requested
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                "page": "home",
                "message": "Welcome to our Custom Printing Website!",
                "featured_products": [
                    {
                        "product_id": p['product_id'],
                        "product_name": p['product_name'],
                        "description": StringHelper.truncate_text(p.get('description'), 100),
                        "base_price": float(p['base_price']),
                        "slug": StringHelper.slugify(p['product_name'])
                    }
                    for p in featured_products
                ],
                "categories": [
                    {
                        "category_id": c['category_id'],
                        "category_name": c['category_name'],
                        "description": StringHelper.truncate_text(c.get('description'), 100),
                        "slug": StringHelper.slugify(c['category_name'])
                    }
                    for c in categories
                ],
                "popular_products": [
                    {
                        "product_id": p[0]['product_id'],
                        "product_name": p[0]['product_name'],
                        "base_price": float(p[0]['base_price']),
                        "order_count": p[1]
                    }
                    for p in popular_products
                ]
            }), 200
        
        # Return HTML page
        return render_template('index.html',
                             featured_products=featured_products,
                             categories=categories,
                             popular_products=popular_products)
    
    except Exception as e:
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({'error': f'Failed to load homepage: {str(e)}'}), 500
        return render_template('error.html', error="Failed to load homepage"), 500


# ============================================
# ABOUT PAGE
# ============================================

"""
    GET /about
    About page with company information

    Returns:
        HTML page or JSON
"""
@main_bp.route('/about', methods=['GET'])
def about():

    about_info = {
        "page": "about",
        "company_name": "Custom Print Shop",
        "tagline": "Your Vision, Our Precision",
        "description": "We provide high-quality custom printing services for all your needs. "
                      "From personalized t-shirts to custom mugs, we bring your ideas to life.",
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
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(about_info), 200
    
    return render_template('about.html', about=about_info)


# ============================================
# CONTACT PAGE
# ============================================
"""
    GET /contact
    Contact page with form and information

    Returns:
        HTML page or JSON
"""
@main_bp.route('/contact', methods=['GET'])
def contact():
    contact_info = {
        "page": "contact",
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
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(contact_info), 200
    
    return render_template('contact.html', contact=contact_info)

 


# ============================================
# FEATURES PAGE
# ============================================
"""
    GET /features
    Display platform features and capabilities
    
    Returns:
        HTML page or JSON
"""
@main_bp.route('/features', methods=['GET'])
def features():
    
    features_list = {
        "page": "features",
        "features": [
            {
                "title": "Easy Design Upload",
                "description": "Upload your designs in various formats including PNG, JPG, PDF, AI, and SVG",
                "icon": "upload"
            },
            {
                "title": "Real-time Preview",
                "description": "See how your design will look on the final product before ordering",
                "icon": "eye"
            },
            {
                "title": "Custom Text & Graphics",
                "description": "Add custom text, choose fonts, colors, and positioning",
                "icon": "edit"
            },
            {
                "title": "Bulk Ordering",
                "description": "Order in bulk and save with our quantity discounts",
                "icon": "shopping-cart"
            },
            {
                "title": "Fast Production",
                "description": "Most orders shipped within 2-3 business days",
                "icon": "clock"
            },
            {
                "title": "Quality Guarantee",
                "description": "100% satisfaction guaranteed or your money back",
                "icon": "shield"
            }
        ]
    }
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(features_list), 200
    
    return render_template('features.html', features=features_list)


# ============================================
# FAQ PAGE
# ============================================
@main_bp.route('/faq', methods=['GET'])
def faq():
    """
    GET /faq
    Frequently Asked Questions
    
    Returns:
        HTML page or JSON
    """
    faqs = {
        "page": "faq",
        "categories": [
            {
                "category": "Ordering",
                "questions": [
                    {
                        "question": "How do I place an order?",
                        "answer": "Browse our products, select the item you want, upload your design or add custom text, and checkout."
                    },
                    {
                        "question": "What file formats do you accept?",
                        "answer": "We accept PNG, JPG, PDF, AI, SVG, PSD, and EPS formats."
                    },
                    {
                        "question": "Can I order without an account?",
                        "answer": "Yes! You can checkout as a guest, though creating an account lets you track orders and save designs."
                    }
                ]
            },
            {
                "category": "Shipping & Delivery",
                "questions": [
                    {
                        "question": "How long does shipping take?",
                        "answer": "Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available."
                    },
                    {
                        "question": "Do you ship internationally?",
                        "answer": "Currently we only ship within the United States."
                    },
                    {
                        "question": "Can I track my order?",
                        "answer": "Yes! You'll receive a tracking number via email once your order ships."
                    }
                ]
            },
            {
                "category": "Design & Customization",
                "questions": [
                    {
                        "question": "What if I don't have a design?",
                        "answer": "We offer design templates and text customization tools. You can also contact us for design assistance."
                    },
                    {
                        "question": "What's the minimum image resolution?",
                        "answer": "For best quality, we recommend at least 300 DPI at the final print size."
                    },
                    {
                        "question": "Can I see a proof before printing?",
                        "answer": "Yes! We provide a digital proof for approval before production begins."
                    }
                ]
            },
            {
                "category": "Returns & Refunds",
                "questions": [
                    {
                        "question": "What is your return policy?",
                        "answer": "We offer full refunds within 30 days if you're not satisfied with the quality."
                    },
                    {
                        "question": "Can I cancel my order?",
                        "answer": "Orders can be cancelled within 2 hours of placement, before production begins."
                    }
                ]
            }
        ]
    }
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(faqs), 200
    
    return render_template('faq.html', faqs=faqs)


# ============================================
# PRIVACY POLICY
# ============================================
@main_bp.route('/privacy', methods=['GET'])
def privacy():
    """
    GET /privacy
    Privacy policy page
    
    Returns:
        HTML page or JSON
    """
    privacy_info = {
        "page": "privacy",
        "last_updated": "2025-01-01",
        "sections": [
            {
                "title": "Information We Collect",
                "content": "We collect information you provide when creating an account, placing orders, and contacting us."
            },
            {
                "title": "How We Use Your Information",
                "content": "Your information is used to process orders, communicate with you, and improve our services."
            },
            {
                "title": "Data Security",
                "content": "We use industry-standard security measures to protect your personal information."
            },
            {
                "title": "Cookies",
                "content": "We use cookies to enhance your browsing experience and remember your preferences."
            }
        ]
    }
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(privacy_info), 200
    
    return render_template('privacy.html', privacy=privacy_info)


# ============================================
# TERMS OF SERVICE
# ============================================
@main_bp.route('/terms', methods=['GET'])
def terms():
    """
    GET /terms
    Terms of service page
    
    Returns:
        HTML page or JSON
    """
    terms_info = {
        "page": "terms",
        "last_updated": "2025-01-01",
        "sections": [
            {
                "title": "Acceptance of Terms",
                "content": "By using our service, you agree to these terms and conditions."
            },
            {
                "title": "User Responsibilities",
                "content": "You are responsible for the content you upload and ensuring you have rights to use it."
            },
            {
                "title": "Copyright & Intellectual Property",
                "content": "You must own or have permission to use any designs you submit for printing."
            },
            {
                "title": "Order Accuracy",
                "content": "Please review your order carefully before submitting. We are not responsible for user errors."
            }
        ]
    }
    
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify(terms_info), 200
    
    return render_template('terms.html', terms=terms_info)


# ============================================
# SEARCH
# ============================================
@main_bp.route('/search', methods=['GET'])
def search():
    """
    GET /search
    Global site search
    
    Query Parameters:
        - q: search query (required)
        - category: category filter (optional)
        - limit: results limit (default: 20)
    
    Returns:
        JSON search results
    """
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    limit = min(request.args.get('limit', 20, type=int), 100)
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    if len(query) < 2:
        return jsonify({'error': 'Search query must be at least 2 characters'}), 400
    
    try:
        # Search products
        products = ProductService.search_products(
            search_query=query,
            category_id=category_id,
            limit=limit
        )
        
        # Format results
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
                }
                for p in products
            ]
        }
        
        return jsonify(results), 200
    
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


# ============================================
# SITE MAP
# ============================================
@main_bp.route('/sitemap', methods=['GET'])
def sitemap():
    """
    GET /sitemap
    Site map for navigation
    
    Returns:
        JSON site structure
    """
    site_structure = {
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
            {"name": "Privacy Policy", "path": "/privacy"},
            {"name": "Terms of Service", "path": "/terms"}
        ]
    }
    
    return jsonify(site_structure), 200


# ============================================
# HEALTH CHECK
# ============================================
@main_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /health
    Health check endpoint for monitoring
    
    Returns:
        JSON health status
    """
    from app.database import health_check as db_health_check
    
    try:
        db_health = db_health_check()
        
        health_status = {
            "status": "healthy" if db_health['status'] == 'healthy' else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_health['status'],
            "response_time_ms": db_health.get('response_time_ms')
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 503


# ============================================
# ERROR HANDLERS
# ============================================
@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Page not found'}), 404
    return render_template('404.html'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500