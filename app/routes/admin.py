"""
Admin Routes
Handles admin panel operations (orders, products, customers, reports)
"""

from flask import Blueprint, request, jsonify, session
from sqlalchemy import func, case
from datetime import datetime, timedelta

from app.database import get_db_session
from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)
from app.routes.auth import admin_required, permission_required

# Create blueprint
admin_bp = Blueprint('admin', __name__)


# ============================================
# DASHBOARD
# ============================================

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard():
    """
    Get admin dashboard statistics
    
    Returns:
        JSON with key metrics
    """
    try:
        with get_db_session() as db_session:
            # Get date ranges
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Order statistics
            total_orders = db_session.query(Order).count()
            pending_orders = db_session.query(Order).filter_by(order_status='pending').count()
            processing_orders = db_session.query(Order).filter_by(order_status='processing').count()
            
            # Revenue statistics (completed orders only)
            total_revenue = db_session.query(
                func.sum(Order.total_amount)
            ).filter_by(order_status='completed').scalar() or 0
            
            month_revenue = db_session.query(
                func.sum(Order.total_amount)
            ).filter(
                Order.order_status == 'completed',
                func.date(Order.created_at) >= month_ago
            ).scalar() or 0
            
            # Customer statistics
            total_customers = db_session.query(Customer).count()
            active_customers = db_session.query(Customer).filter_by(is_active=True).count()
            
            # Product statistics
            total_products = db_session.query(Product).count()
            active_products = db_session.query(Product).filter_by(is_active=True).count()
            
            # Recent orders
            recent_orders = db_session.query(Order).order_by(
                Order.created_at.desc()
            ).limit(5).all()
            
            recent_orders_data = [
                {
                    'order_id': o.order_id,
                    'order_number': o.order_number,
                    'customer_name': o.get_customer_name(),
                    'total_amount': float(o.total_amount),
                    'order_status': o.order_status,
                    'created_at': o.created_at.isoformat() if o.created_at else None
                }
                for o in recent_orders
            ]
            
            return jsonify({
                'dashboard': {
                    'orders': {
                        'total': total_orders,
                        'pending': pending_orders,
                        'processing': processing_orders
                    },
                    'revenue': {
                        'total': float(total_revenue),
                        'month': float(month_revenue)
                    },
                    'customers': {
                        'total': total_customers,
                        'active': active_customers
                    },
                    'products': {
                        'total': total_products,
                        'active': active_products
                    },
                    'recent_orders': recent_orders_data
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard: {str(e)}'}), 500


# ============================================
# ORDER MANAGEMENT
# ============================================

@admin_bp.route('/orders', methods=['GET'])
@permission_required('view_orders')
def get_all_orders():
    """
    Get all orders with filtering
    
    Query Parameters:
        - status: string (optional)
        - start_date: string (optional, ISO format)
        - end_date: string (optional, ISO format)
        - page: int (optional, default=1)
        - per_page: int (optional, default=20)
    
    Returns:
        JSON list of orders
    """
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        with get_db_session() as db_session:
            query = db_session.query(Order)
            
            # Filter by status
            if status_filter:
                query = query.filter_by(order_status=status_filter)
            
            # Filter by date range
            if start_date:
                query = query.filter(Order.created_at >= datetime.fromisoformat(start_date))
            if end_date:
                query = query.filter(Order.created_at <= datetime.fromisoformat(end_date))
            
            # Order by date (newest first)
            query = query.order_by(Order.created_at.desc())
            
            # Get total count
            total_orders = query.count()
            
            # Pagination
            offset = (page - 1) * per_page
            orders = query.offset(offset).limit(per_page).all()
            
            # Format results
            result = []
            for order in orders:
                result.append({
                    'order_id': order.order_id,
                    'order_number': order.order_number,
                    'customer_name': order.get_customer_name(),
                    'customer_email': order.get_customer_email(),
                    'order_status': order.order_status,
                    'total_amount': float(order.total_amount),
                    'total_items': order.get_total_items(),
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None
                })
            
            # Pagination info
            total_pages = (total_orders + per_page - 1) // per_page
            
            return jsonify({
                'orders': result,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_orders': total_orders,
                    'total_pages': total_pages
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get orders: {str(e)}'}), 500


@admin_bp.route('/orders/<int:order_id>', methods=['GET'])
@permission_required('view_orders')
def get_order_details(order_id):
    """
    Get order details
    
    Returns:
        JSON order details with items and history
    """
    try:
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Format order items
            items = []
            for item in order.order_items:
                customizations = {c.customization_key: c.customization_value for c in item.customizations}
                items.append({
                    'product_name': item.product.product_name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'subtotal': float(item.subtotal),
                    'customizations': customizations
                })
            
            # Format status history
            history = [
                {
                    'status': h.status,
                    'changed_at': h.changed_at.isoformat() if h.changed_at else None,
                    'changed_by': h.get_changed_by_name(),
                    'notes': h.notes
                }
                for h in order.status_history
            ]
            
            return jsonify({
                'order': {
                    'order_id': order.order_id,
                    'order_number': order.order_number,
                    'customer_name': order.get_customer_name(),
                    'customer_email': order.get_customer_email(),
                    'order_status': order.order_status,
                    'total_amount': float(order.total_amount),
                    'shipping_address': order.shipping_address,
                    'contact_phone': order.contact_phone,
                    'notes': order.notes,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'items': items,
                    'status_history': history
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order details: {str(e)}'}), 500


@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@permission_required('update_order_status')
def update_order_status(order_id):
    """
    Update order status
    
    PUT JSON:
        - status: string (required) - pending, processing, completed, cancelled
        - notes: string (optional)
    
    Returns:
        JSON success message
    """
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    if new_status not in ['pending', 'processing', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            old_status = order.order_status
            
            # Update order status
            order.order_status = new_status
            order.updated_at = datetime.now()
            order.updated_by = session['admin_id']
            
            # Add status history
            status_history = OrderStatusHistory(
                order_id=order_id,
                status=new_status,
                changed_by=session['admin_id'],
                notes=notes
            )
            db_session.add(status_history)
            
            # Log admin activity
            activity_log = AdminActivityLog(
                admin_id=session['admin_id'],
                action='update_order_status',
                table_name='orders',
                record_id=order_id,
                old_values={'order_status': old_status},
                new_values={'order_status': new_status, 'notes': notes}
            )
            db_session.add(activity_log)
            
            return jsonify({
                'message': 'Order status updated successfully',
                'order_status': new_status
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update order status: {str(e)}'}), 500


# ============================================
# PRODUCT MANAGEMENT
# ============================================

@admin_bp.route('/products', methods=['GET'])
@permission_required('view_products')
def get_all_products():
    """
    Get all products
    
    Query Parameters:
        - category_id: int (optional)
        - is_active: boolean (optional)
        - page: int (optional, default=1)
        - per_page: int (optional, default=20)
    
    Returns:
        JSON list of products
    """
    category_id = request.args.get('category_id', type=int)
    is_active_str = request.args.get('is_active')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        with get_db_session() as db_session:
            query = db_session.query(Product)
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            if is_active_str:
                is_active = is_active_str.lower() == 'true'
                query = query.filter_by(is_active=is_active)
            
            query = query.order_by(Product.product_name)
            
            # Get total count
            total_products = query.count()
            
            # Pagination
            offset = (page - 1) * per_page
            products = query.offset(offset).limit(per_page).all()
            
            # Format results
            result = [
                {
                    'product_id': p.product_id,
                    'product_name': p.product_name,
                    'description': p.description,
                    'base_price': float(p.base_price),
                    'category_name': p.category.category_name,
                    'is_active': p.is_active,
                    'times_ordered': p.get_times_ordered(),
                    'total_revenue': float(p.get_total_revenue() or 0)
                }
                for p in products
            ]
            
            return jsonify({
                'products': result,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_products': total_products
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500


@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@permission_required('update_product')
def update_product(product_id):
    """
    Update product
    
    PUT JSON:
        - product_name: string (optional)
        - description: string (optional)
        - base_price: float (optional)
        - is_active: boolean (optional)
    
    Returns:
        JSON success message
    """
    data = request.get_json()
    
    try:
        with get_db_session() as db_session:
            product = db_session.query(Product).filter_by(product_id=product_id).first()
            
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            # Store old values
            old_values = {
                'product_name': product.product_name,
                'base_price': float(product.base_price),
                'is_active': product.is_active
            }
            
            # Update fields
            if 'product_name' in data:
                product.product_name = data['product_name']
            if 'description' in data:
                product.description = data['description']
            if 'base_price' in data:
                product.base_price = data['base_price']
            if 'is_active' in data:
                product.is_active = data['is_active']
            
            product.updated_at = datetime.now()
            product.updated_by = session['admin_id']
            
            # Log activity
            activity_log = AdminActivityLog(
                admin_id=session['admin_id'],
                action='update_product',
                table_name='products',
                record_id=product_id,
                old_values=old_values,
                new_values=data
            )
            db_session.add(activity_log)
            
            return jsonify({'message': 'Product updated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update product: {str(e)}'}), 500


# ============================================
# CUSTOMER MANAGEMENT
# ============================================

@admin_bp.route('/customers', methods=['GET'])
@permission_required('view_customers')
def get_all_customers():
    """
    Get all customers
    
    Query Parameters:
        - page: int (optional, default=1)
        - per_page: int (optional, default=20)
    
    Returns:
        JSON list of customers
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        with get_db_session() as db_session:
            query = db_session.query(Customer).order_by(Customer.created_at.desc())
            
            # Get total count
            total_customers = query.count()
            
            # Pagination
            offset = (page - 1) * per_page
            customers = query.offset(offset).limit(per_page).all()
            
            # Format results
            result = [
                {
                    'customer_id': c.customer_id,
                    'username': c.username,
                    'email': c.email,
                    'full_name': c.full_name,
                    'phone_number': c.phone_number,
                    'is_active': c.is_active,
                    'total_orders': c.get_order_count(),
                    'total_spent': float(c.get_total_spent()),
                    'created_at': c.created_at.isoformat() if c.created_at else None
                }
                for c in customers
            ]
            
            return jsonify({
                'customers': result,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_customers': total_customers
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customers: {str(e)}'}), 500


# ============================================
# REPORTS
# ============================================

@admin_bp.route('/reports/sales', methods=['GET'])
@permission_required('view_reports')
def get_sales_report():
    """
    Get sales report
    
    Query Parameters:
        - start_date: string (optional, ISO format)
        - end_date: string (optional, ISO format)
        - group_by: string (optional) - day, week, month
    
    Returns:
        JSON sales statistics
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')
    
    try:
        with get_db_session() as db_session:
            query = db_session.query(Order).filter_by(order_status='completed')
            
            if start_date:
                query = query.filter(Order.created_at >= datetime.fromisoformat(start_date))
            if end_date:
                query = query.filter(Order.created_at <= datetime.fromisoformat(end_date))
            
            orders = query.all()
            
            # Calculate statistics
            total_revenue = sum(float(o.total_amount) for o in orders)
            total_orders = len(orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            return jsonify({
                'sales_report': {
                    'total_revenue': total_revenue,
                    'total_orders': total_orders,
                    'average_order_value': avg_order_value,
                    'start_date': start_date,
                    'end_date': end_date
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate sales report: {str(e)}'}), 500


@admin_bp.route('/reports/products', methods=['GET'])
@permission_required('view_reports')
def get_product_report():
    """
    Get product performance report
    
    Returns:
        JSON product statistics
    """
    try:
        with get_db_session() as db_session:
            # Get product performance
            products = db_session.query(Product).all()
            
            product_data = []
            for product in products:
                product_data.append({
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'category_name': product.category.category_name,
                    'base_price': float(product.base_price),
                    'times_ordered': product.get_times_ordered(),
                    'total_quantity_sold': product.get_total_quantity_sold(),
                    'total_revenue': float(product.get_total_revenue() or 0)
                })
            
            # Sort by revenue
            product_data.sort(key=lambda x: x['total_revenue'], reverse=True)
            
            return jsonify({
                'product_report': {
                    'products': product_data[:20],  # Top 20
                    'total_products': len(products)
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate product report: {str(e)}'}), 500