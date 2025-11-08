"""
File Service
Business logic for file upload and management
"""

import os
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

from app.database import get_db_session
from app.models import UploadedFile, CartItem, OrderItem


class FileService:
    """Service class for file operations"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    @staticmethod
    def allowed_file(filename):
        """
        Check if file extension is allowed
        
        Args:
            filename (str): Filename to check
            
        Returns:
            bool: True if allowed
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in FileService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def generate_unique_filename(original_filename):
        """
        Generate unique filename
        
        Args:
            original_filename (str): Original filename
            
        Returns:
            str: Unique filename
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(secure_filename(original_filename))
        unique_id = uuid.uuid4().hex[:8]
        return f"{name}_{timestamp}_{unique_id}{ext}"
    
    @staticmethod
    def get_file_path(filename, customer_id=None, session_id=None):
        """
        Get file path for storage
        
        Args:
            filename (str): Filename
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            str: File path relative to static folder
        """
        if customer_id:
            folder = f"customer_{customer_id}"
        elif session_id:
            folder = f"guest_{session_id}"
        else:
            folder = "general"
        
        unique_filename = FileService.generate_unique_filename(filename)
        return os.path.join('uploads', folder, unique_filename)
    
    @staticmethod
    def save_file(file, customer_id=None, session_id=None, 
                  cart_item_id=None, order_item_id=None, upload_folder=None):
        """
        Save uploaded file
        
        Args:
            file: FileStorage object
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            cart_item_id (int, optional): Cart item ID to associate
            order_item_id (int, optional): Order item ID to associate
            upload_folder (str): Base upload folder path
            
        Returns:
            tuple: (success: bool, uploaded_file or error_message)
        """
        if not file or file.filename == '':
            return False, "No file provided"
        
        if not FileService.allowed_file(file.filename):
            return False, "File type not allowed"
        
        try:
            # Generate file path
            file_path = FileService.get_file_path(
                file.filename, customer_id, session_id
            )
            
            # Create directory if needed
            directory = os.path.dirname(file_path)
            full_directory = os.path.join(upload_folder, directory)
            os.makedirs(full_directory, exist_ok=True)
            
            # Save file
            full_path = os.path.join(upload_folder, file_path)
            file.save(full_path)
            
            # Create database record
            with get_db_session() as session:
                uploaded_file = UploadedFile(
                    customer_id=customer_id,
                    session_id=session_id,
                    cart_item_id=cart_item_id,
                    order_item_id=order_item_id,
                    file_url=f"/static/{file_path}",
                    original_filename=file.filename
                )
                session.add(uploaded_file)
                session.flush()
                
                # Update cart item or order item
                if cart_item_id:
                    cart_item = session.query(CartItem).filter_by(
                        cart_item_id=cart_item_id
                    ).first()
                    if cart_item:
                        cart_item.design_file_url = uploaded_file.file_url
                
                if order_item_id:
                    order_item = session.query(OrderItem).filter_by(
                        order_item_id=order_item_id
                    ).first()
                    if order_item:
                        order_item.design_file_url = uploaded_file.file_url
                
                return True, uploaded_file
                
        except Exception as e:
            return False, f"Failed to save file: {str(e)}"
    
    @staticmethod
    def save_multiple_files(files, customer_id=None, session_id=None, upload_folder=None):
        """
        Save multiple uploaded files
        
        Args:
            files: List of FileStorage objects
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            upload_folder (str): Base upload folder path
            
        Returns:
            tuple: (uploaded_files: list, errors: list)
        """
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            success, result = FileService.save_file(
                file, customer_id, session_id, 
                upload_folder=upload_folder
            )
            
            if success:
                uploaded_files.append(result)
            else:
                errors.append(f"{file.filename}: {result}")
        
        return uploaded_files, errors
    
    @staticmethod
    def get_file_by_id(file_id):
        """
        Get file by ID
        
        Args:
            file_id (int): File ID
            
        Returns:
            UploadedFile or None
        """
        try:
            with get_db_session() as session:
                return session.query(UploadedFile).filter_by(
                    file_id=file_id
                ).first()
        except Exception:
            return None
    
    @staticmethod
    def get_user_files(customer_id=None, session_id=None):
        """
        Get all files for a user
        
        Args:
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            list: List of uploaded files
        """
        try:
            with get_db_session() as session:
                if customer_id:
                    files = session.query(UploadedFile).filter_by(
                        customer_id=customer_id
                    ).order_by(UploadedFile.uploaded_at.desc()).all()
                elif session_id:
                    files = session.query(UploadedFile).filter_by(
                        session_id=session_id
                    ).order_by(UploadedFile.uploaded_at.desc()).all()
                else:
                    files = []
                
                return files
        except Exception:
            return []
    
    @staticmethod
    def delete_file(file_id, customer_id=None, session_id=None, upload_folder=None):
        """
        Delete file
        
        Args:
            file_id (int): File ID
            customer_id (int, optional): Customer ID for ownership check
            session_id (str, optional): Session ID for ownership check
            upload_folder (str): Base upload folder path
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                file = session.query(UploadedFile).filter_by(
                    file_id=file_id
                ).first()
                
                if not file:
                    return False, "File not found"
                
                # Verify ownership
                if customer_id and file.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and file.session_id != session_id:
                    return False, "Access denied"
                
                # Don't delete if attached to order
                if file.order_item_id:
                    return False, "Cannot delete file attached to an order"
                
                # Delete physical file
                try:
                    file_path = file.file_url.replace('/static/', '')
                    full_path = os.path.join(upload_folder, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting physical file: {e}")
                
                # Delete database record
                session.delete(file)
                
                return True, "File deleted successfully"
                
        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"
    
    @staticmethod
    def verify_file_ownership(file_id, customer_id=None, session_id=None, is_admin=False):
        """
        Verify file ownership
        
        Args:
            file_id (int): File ID
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            is_admin (bool): Is admin user
            
        Returns:
            bool: True if user has access
        """
        try:
            with get_db_session() as session:
                file = session.query(UploadedFile).filter_by(
                    file_id=file_id
                ).first()
                
                if not file:
                    return False
                
                # Admins can access all files
                if is_admin:
                    return True
                
                # Check ownership
                if customer_id and file.customer_id == customer_id:
                    return True
                if session_id and file.session_id == session_id:
                    return True
                
                return False
        except Exception:
            return False
    
    @staticmethod
    def get_file_statistics(customer_id=None):
        """
        Get file statistics for a customer
        
        Args:
            customer_id (int, optional): Customer ID
            
        Returns:
            dict: File statistics
        """
        try:
            with get_db_session() as session:
                if customer_id:
                    files = session.query(UploadedFile).filter_by(
                        customer_id=customer_id
                    ).all()
                else:
                    return {'total_files': 0}
                
                return {
                    'total_files': len(files),
                    'files_in_cart': sum(1 for f in files if f.cart_item_id),
                    'files_in_orders': sum(1 for f in files if f.order_item_id),
                    'unassigned_files': sum(1 for f in files if not f.cart_item_id and not f.order_item_id)
                }
        except Exception:
            return {'total_files': 0}
    
    @staticmethod
    def cleanup_orphaned_files(days_old=30):
        """
        Clean up orphaned files (not attached to cart or order)
        
        Args:
            days_old (int): Delete files older than this many days
            
        Returns:
            int: Number of files deleted
        """
        try:
            with get_db_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                orphaned_files = session.query(UploadedFile).filter(
                    UploadedFile.cart_item_id == None,
                    UploadedFile.order_item_id == None,
                    UploadedFile.uploaded_at < cutoff_date
                ).all()
                
                count = 0
                for file in orphaned_files:
                    try:
                        # Delete physical file
                        file_path = file.file_url.replace('/static/', '')
                        # Note: Need upload_folder path here
                        # os.remove(full_path)
                        
                        # Delete database record
                        session.delete(file)
                        count += 1
                    except Exception as e:
                        print(f"Error deleting orphaned file: {e}")
                
                return count
        except Exception as e:
            print(f"Error cleaning up files: {e}")
            return 0
    
    @staticmethod
    def get_file_info():
        """
        Get upload configuration info
        
        Returns:
            dict: Upload configuration
        """
        return {
            'allowed_extensions': list(FileService.ALLOWED_EXTENSIONS),
            'max_file_size_bytes': FileService.MAX_FILE_SIZE,
            'max_file_size_mb': FileService.MAX_FILE_SIZE / (1024 * 1024),
            'max_files_per_upload': 10
        }