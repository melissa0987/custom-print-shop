"""
Files Routes
Handles file uploads for custom designs
"""

from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from app.database import get_db_session
from app.models import UploadedFile, CartItem, OrderItem, Customer

# Create blueprint
files_bp = Blueprint('files', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_path(filename, folder='general'):
    """
    Generate file path for uploaded file
    
    Args:
        filename: Original filename
        folder: Subfolder (customer_id, session_id, or 'general')
    
    Returns:
        Relative file path
    """
    # Create unique filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(secure_filename(filename))
    unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Construct path: uploads/folder/filename
    return os.path.join('uploads', folder, unique_filename)


def ensure_upload_directory(directory):
    """Create upload directory if it doesn't exist"""
    full_path = os.path.join(current_app.root_path, 'static', directory)
    os.makedirs(full_path, exist_ok=True)
    return full_path


# ============================================
# FILE UPLOAD
# ============================================

@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload design file
    
    Form Data:
        - file: file (required)
        - cart_item_id: int (optional) - associate with cart item
        - order_item_id: int (optional) - associate with order item
    
    Returns:
        JSON with file info
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Get optional parameters
    cart_item_id = request.form.get('cart_item_id', type=int)
    order_item_id = request.form.get('order_item_id', type=int)
    
    try:
        with get_db_session() as db_session:
            # Determine owner (customer or guest session)
            if 'customer_id' in session:
                customer_id = session['customer_id']
                session_id = None
                folder = f"customer_{customer_id}"
            elif 'session_id' in session:
                customer_id = None
                session_id = session['session_id']
                folder = f"guest_{session_id}"
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Generate file path
            file_path = get_file_path(file.filename, folder)
            
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            full_directory = ensure_upload_directory(directory)
            
            # Save file
            full_file_path = os.path.join(current_app.root_path, 'static', file_path)
            file.save(full_file_path)
            
            # Create database record
            uploaded_file = UploadedFile(
                customer_id=customer_id,
                session_id=session_id,
                cart_item_id=cart_item_id,
                order_item_id=order_item_id,
                file_url=f"/static/{file_path}",
                original_filename=file.filename
            )
            db_session.add(uploaded_file)
            db_session.flush()
            
            # Update cart item or order item with file URL
            if cart_item_id:
                cart_item = db_session.query(CartItem).filter_by(
                    cart_item_id=cart_item_id
                ).first()
                if cart_item:
                    cart_item.design_file_url = uploaded_file.file_url
            
            if order_item_id:
                order_item = db_session.query(OrderItem).filter_by(
                    order_item_id=order_item_id
                ).first()
                if order_item:
                    order_item.design_file_url = uploaded_file.file_url
            
            return jsonify({
                'message': 'File uploaded successfully',
                'file': {
                    'file_id': uploaded_file.file_id,
                    'file_url': uploaded_file.file_url,
                    'original_filename': uploaded_file.original_filename,
                    'uploaded_at': uploaded_file.uploaded_at.isoformat() if uploaded_file.uploaded_at else None
                }
            }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500


@files_bp.route('/upload-multiple', methods=['POST'])
def upload_multiple_files():
    """
    Upload multiple design files
    
    Form Data:
        - files: file[] (required) - multiple files
    
    Returns:
        JSON with uploaded files info
    """
    # Check if files are in request
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({'error': 'No files selected'}), 400
    
    # Limit number of files
    if len(files) > 10:
        return jsonify({'error': 'Maximum 10 files allowed'}), 400
    
    try:
        with get_db_session() as db_session:
            # Determine owner
            if 'customer_id' in session:
                customer_id = session['customer_id']
                session_id = None
                folder = f"customer_{customer_id}"
            elif 'session_id' in session:
                customer_id = None
                session_id = session['session_id']
                folder = f"guest_{session_id}"
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            uploaded_files = []
            errors = []
            
            for file in files:
                if file.filename == '':
                    continue
                
                if not allowed_file(file.filename):
                    errors.append(f"{file.filename}: File type not allowed")
                    continue
                
                try:
                    # Generate file path
                    file_path = get_file_path(file.filename, folder)
                    
                    # Ensure directory exists
                    directory = os.path.dirname(file_path)
                    ensure_upload_directory(directory)
                    
                    # Save file
                    full_file_path = os.path.join(current_app.root_path, 'static', file_path)
                    file.save(full_file_path)
                    
                    # Create database record
                    uploaded_file = UploadedFile(
                        customer_id=customer_id,
                        session_id=session_id,
                        file_url=f"/static/{file_path}",
                        original_filename=file.filename
                    )
                    db_session.add(uploaded_file)
                    db_session.flush()
                    
                    uploaded_files.append({
                        'file_id': uploaded_file.file_id,
                        'file_url': uploaded_file.file_url,
                        'original_filename': uploaded_file.original_filename
                    })
                    
                except Exception as e:
                    errors.append(f"{file.filename}: {str(e)}")
            
            return jsonify({
                'message': f'{len(uploaded_files)} files uploaded successfully',
                'files': uploaded_files,
                'errors': errors if errors else None
            }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to upload files: {str(e)}'}), 500


# ============================================
# FILE RETRIEVAL
# ============================================

@files_bp.route('/', methods=['GET'])
@files_bp.route('/list', methods=['GET'])
def get_files():
    """
    Get uploaded files for current user
    
    Returns:
        JSON list of files
    """
    try:
        with get_db_session() as db_session:
            if 'customer_id' in session:
                files = db_session.query(UploadedFile).filter_by(
                    customer_id=session['customer_id']
                ).order_by(UploadedFile.uploaded_at.desc()).all()
            elif 'session_id' in session:
                files = db_session.query(UploadedFile).filter_by(
                    session_id=session['session_id']
                ).order_by(UploadedFile.uploaded_at.desc()).all()
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            result = [
                {
                    'file_id': f.file_id,
                    'file_url': f.file_url,
                    'original_filename': f.original_filename,
                    'uploaded_at': f.uploaded_at.isoformat() if f.uploaded_at else None,
                    'is_image': f.is_image(),
                    'is_pdf': f.is_pdf()
                }
                for f in files
            ]
            
            return jsonify({'files': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get files: {str(e)}'}), 500


@files_bp.route('/<int:file_id>', methods=['GET'])
def get_file(file_id):
    """
    Get file details
    
    Returns:
        JSON file info
    """
    try:
        with get_db_session() as db_session:
            file = db_session.query(UploadedFile).filter_by(file_id=file_id).first()
            
            if not file:
                return jsonify({'error': 'File not found'}), 404
            
            # Check ownership
            if 'customer_id' in session:
                if file.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if file.session_id != session['session_id']:
                    return jsonify({'error': 'Access denied'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            return jsonify({
                'file': {
                    'file_id': file.file_id,
                    'file_url': file.file_url,
                    'original_filename': file.original_filename,
                    'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None,
                    'is_image': file.is_image(),
                    'is_pdf': file.is_pdf(),
                    'cart_item_id': file.cart_item_id,
                    'order_item_id': file.order_item_id
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get file: {str(e)}'}), 500


# ============================================
# FILE DELETION
# ============================================

@files_bp.route('/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    Delete uploaded file
    
    Returns:
        JSON success message
    """
    try:
        with get_db_session() as db_session:
            file = db_session.query(UploadedFile).filter_by(file_id=file_id).first()
            
            if not file:
                return jsonify({'error': 'File not found'}), 404
            
            # Check ownership
            if 'customer_id' in session:
                if file.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if file.session_id != session['session_id']:
                    return jsonify({'error': 'Access denied'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Don't allow deletion if file is attached to an order
            if file.order_item_id:
                return jsonify({'error': 'Cannot delete file attached to an order'}), 400
            
            # Delete physical file
            try:
                file_path = file.file_url.replace('/static/', '')
                full_path = os.path.join(current_app.root_path, 'static', file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                # Log error but continue with database deletion
                print(f"Error deleting physical file: {str(e)}")
            
            # Delete database record
            db_session.delete(file)
            
            return jsonify({'message': 'File deleted successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


# ============================================
# FILE DOWNLOAD
# ============================================

@files_bp.route('/<int:file_id>/download', methods=['GET'])
def download_file(file_id):
    """
    Download file
    
    Returns:
        File download
    """
    try:
        with get_db_session() as db_session:
            file = db_session.query(UploadedFile).filter_by(file_id=file_id).first()
            
            if not file:
                return jsonify({'error': 'File not found'}), 404
            
            # Check ownership (customers or admins can download)
            has_access = False
            if 'customer_id' in session and file.customer_id == session['customer_id']:
                has_access = True
            elif 'session_id' in session and file.session_id == session['session_id']:
                has_access = True
            elif 'admin_id' in session:
                has_access = True
            
            if not has_access:
                return jsonify({'error': 'Access denied'}), 403
            
            # Get file path
            file_path = file.file_url.replace('/static/', '')
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            full_directory = os.path.join(current_app.root_path, 'static', directory)
            
            return send_from_directory(
                full_directory,
                filename,
                as_attachment=True,
                download_name=file.original_filename
            )
            
    except Exception as e:
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500


# ============================================
# FILE INFO
# ============================================

@files_bp.route('/info', methods=['GET'])
def get_upload_info():
    """
    Get upload configuration info
    
    Returns:
        JSON with allowed file types and size limits
    """
    return jsonify({
        'upload_info': {
            'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'],
            'max_file_size_mb': 16,
            'max_files_per_upload': 10
        }
    }), 200