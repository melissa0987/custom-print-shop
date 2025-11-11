"""
app/routes/files.py
Files Routes
Handles file uploads for custom designs

"""
# TODO: use render_template for html

import os
from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from app.models import UploadedFile
from app.services.file_service import FileService
from app.utils import guest_or_customer

# Create blueprint
files_bp = Blueprint('files', __name__)

# ============================================
# FILE UPLOAD
# ============================================

@files_bp.route('/upload', methods=['POST'])
@guest_or_customer
def upload_file():
    """
    Upload design file
    """
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file provided or selected'}), 400
    
    file = request.files['file']
    cart_item_id = request.form.get('cart_item_id', type=int)
    order_item_id = request.form.get('order_item_id', type=int)
    
    try:
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        success, result = FileService.save_file(
            file=file,
            customer_id=customer_id,
            session_id=session_id,
            cart_item_id=cart_item_id,
            order_item_id=order_item_id,
            upload_folder=upload_folder
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        uploaded_file = result
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file': {
                'file_id': uploaded_file['file_id'],
                'file_url': uploaded_file['file_url'],
                'original_filename': uploaded_file['original_filename'],
                'uploaded_at': uploaded_file['uploaded_at'].isoformat() if uploaded_file.get('uploaded_at') else None
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500


# Upload multiple design files
@files_bp.route('/upload-multiple', methods=['POST'])
@guest_or_customer
def upload_multiple_files(): 
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
        # Get customer/session info from session
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Use FileService to handle bulk upload
        uploaded_files, errors = FileService.save_multiple_files(
            files=files,
            customer_id=customer_id,
            session_id=session_id,
            upload_folder=upload_folder
        )
        
        # Format response
        formatted_files = [
            {
                'file_id': f['file_id'],
                'file_url': f['file_url'],
                'original_filename': f['original_filename']
            }
            for f in uploaded_files
        ]
        
        return jsonify({
            'message': f'{len(uploaded_files)} files uploaded successfully',
            'files': formatted_files,
            'errors': errors if errors else None
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to upload files: {str(e)}'}), 500

# ============================================
# FILE RETRIEVAL
# ============================================

# Get uploaded files for current user
@files_bp.route('/', methods=['GET'])
@files_bp.route('/list', methods=['GET'])
@guest_or_customer
def get_files(): 
    try:
        # Get customer/session info from session
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        
        # Use FileService to get files
        files = FileService.get_user_files(
            customer_id=customer_id,
            session_id=session_id
        )
        
        result = [
            {
                'file_id': f['file_id'],
                'file_url': f['file_url'],
                'original_filename': f['original_filename'],
                'uploaded_at': f['uploaded_at'].isoformat() if f.get('uploaded_at') else None,
                'is_image': UploadedFile.is_image(f['original_filename']),
                'is_pdf': UploadedFile.is_pdf(f['original_filename'])
            }
            for f in files
        ]
        
        return jsonify({'files': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get files: {str(e)}'}), 500


# Get file details by file_id
@files_bp.route('/<int:file_id>', methods=['GET'])
def get_file(file_id): 
    try:
        uploaded_file_model = UploadedFile()
        file = uploaded_file_model.get_by_id(file_id)
        
        if not file:
            return jsonify({'error': 'File not found'}), 404
        
        # Check ownership
        if 'customer_id' in session:
            if file.get('customer_id') != session['customer_id']:
                return jsonify({'error': 'Access denied'}), 403
        elif 'session_id' in session:
            if file.get('session_id') != session['session_id']:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Authentication required'}), 401
        
        return jsonify({
            'file': {
                'file_id': file['file_id'],
                'file_url': file['file_url'],
                'original_filename': file['original_filename'],
                'uploaded_at': file['uploaded_at'].isoformat() if file.get('uploaded_at') else None,
                'is_image': UploadedFile.is_image(file['original_filename']),
                'is_pdf': UploadedFile.is_pdf(file['original_filename']),
                'cart_item_id': file.get('cart_item_id'),
                'order_item_id': file.get('order_item_id')
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get file: {str(e)}'}), 500

# ============================================
# FILE DELETION
# ============================================

# Delete uploaded file
@files_bp.route('/<int:file_id>', methods=['DELETE'])
@guest_or_customer
def delete_file(file_id): 
    try:
        # Get customer/session info from session
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Use FileService to delete file
        success, message = FileService.delete_file(
            file_id=file_id,
            customer_id=customer_id,
            session_id=session_id,
            upload_folder=upload_folder
        )
        
        if not success:
            # Determine appropriate status code
            if 'not found' in message.lower():
                status_code = 404
            elif 'denied' in message.lower():
                status_code = 403
            elif 'cannot delete' in message.lower():
                status_code = 400
            else:
                status_code = 500
            
            return jsonify({'error': message}), status_code
        
        return jsonify({'message': message}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


# ============================================
# FILE DOWNLOAD
# ============================================

# Download file
@files_bp.route('/<int:file_id>/download', methods=['GET'])
def download_file(file_id): 
    try:
        uploaded_file_model = UploadedFile()
        file = uploaded_file_model.get_by_id(file_id)
        
        if not file:
            return jsonify({'error': 'File not found'}), 404
        
        # Check ownership (customers or admins can download)
        has_access = False
        if 'customer_id' in session and file.get('customer_id') == session['customer_id']:
            has_access = True
        elif 'session_id' in session and file.get('session_id') == session['session_id']:
            has_access = True
        elif 'admin_id' in session:
            has_access = True
        
        if not has_access:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get file path
        file_path = file['file_url'].replace('/static/', '')
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        full_directory = os.path.join(current_app.root_path, 'static', directory)
        
        return send_from_directory(
            full_directory,
            filename,
            as_attachment=True,
            download_name=file['original_filename']
        )
            
    except Exception as e:
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500


# ============================================
# FILE INFO
# ============================================
# Get upload configuration info
@files_bp.route('/info', methods=['GET'])
def get_upload_info(): 
    return jsonify({
        'upload_info': {
            'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'],
            'max_file_size_mb': 16,
            'max_files_per_upload': 10
        }
    }), 200