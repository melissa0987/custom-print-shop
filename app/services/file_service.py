"""
File Service
Business logic for file upload and management
"""

import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from uuid import uuid4

from app.database import get_db_session
from app.models.__models_init__ import UploadedFile, CartItem, OrderItem
from app.utils.helpers import FileHelper
from app.utils.validators import Validators


class FileService:
    """Service class for file operations"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    """Check if the file extension is allowed."""
    @staticmethod
    def allowed_file(filename): 
        return Validators.validate_file_extension(filename, FileService.ALLOWED_EXTENSIONS)
    
    """Generate a unique, safe filename."""
    @staticmethod
    def generate_unique_filename(original_filename):
         
        return FileHelper.generate_unique_filename(original_filename)

    
    # Get file path for storage
    @staticmethod
    def get_file_path(filename, customer_id=None, session_id=None):
        if customer_id:
            folder = f"customer_{customer_id}"
        elif session_id:
            folder = f"guest_{session_id}"
        else:
            folder = "general"

        unique_filename = FileService.generate_unique_filename(filename)
        return os.path.join("uploads", folder, unique_filename)
    
    # Save uploaded file
    @staticmethod
    def save_file(file, customer_id=None, session_id=None, 
                  cart_item_id=None, order_item_id=None, upload_folder=None):
        if not file or file.filename.strip() == "":
            return False, "No file provided"

        if not FileService.allowed_file(file.filename):
            return False, "File type not allowed"

        # Validate file size if possible
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        is_valid_size, msg = Validators.validate_file_size(size, max_size_mb=16)
        if not is_valid_size:
            return False, msg

        try:
            file_path = FileService.get_file_path(file.filename, customer_id, session_id)
            full_path = os.path.join(upload_folder, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            file.save(full_path)

            # Store database record
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

                # Attach to related item if needed
                if cart_item_id:
                    cart_item = session.query(CartItem).filter_by(cart_item_id=cart_item_id).first()
                    if cart_item:
                        cart_item.design_file_url = uploaded_file.file_url

                if order_item_id:
                    order_item = session.query(OrderItem).filter_by(order_item_id=order_item_id).first()
                    if order_item:
                        order_item.design_file_url = uploaded_file.file_url

                return True, uploaded_file

        except Exception as e:
            return False, f"Failed to save file: {str(e)}"
    
    # Save multiple uploaded files.
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
            if not file or file.filename.strip() == "":
                continue

            success, result = FileService.save_file(
                file, customer_id, session_id, upload_folder=upload_folder
            )

            if success:
                uploaded_files.append(result)
            else:
                errors.append(f"{file.filename}: {result}")

        return uploaded_files, errors
    

    # Retrieve file record by ID.
    @staticmethod
    def get_file_by_id(file_id):
        try:
            with get_db_session() as session:
                return session.query(UploadedFile).filter_by(file_id=file_id).first()
        except Exception:
            return None
    
    # Fetch all files associated with a user or guest session.
    @staticmethod
    def get_user_files(customer_id=None, session_id=None):
        try:
            with get_db_session() as session:
                query = session.query(UploadedFile)
                if customer_id:
                    files = query.filter_by(customer_id=customer_id)
                elif session_id:
                    files = query.filter_by(session_id=session_id)
                else:
                    return []
                return files.order_by(UploadedFile.uploaded_at.desc()).all()
        except Exception:
            return []
    
    # Delete a file and its record if user owns it.
    @staticmethod
    def delete_file(file_id, customer_id=None, session_id=None, upload_folder=None):
        try:
            with get_db_session() as session:
                file = session.query(UploadedFile).filter_by(file_id=file_id).first()
                if not file:
                    return False, "File not found"

                # Ownership validation
                if customer_id and file.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and file.session_id != session_id:
                    return False, "Access denied"
                if file.order_item_id:
                    return False, "Cannot delete file attached to an order"

                # Delete physical file
                try:
                    file_path = file.file_url.replace("/static/", "")
                    full_path = os.path.join(upload_folder, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting file from disk: {e}")

                session.delete(file)
                return True, "File deleted successfully"

        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"
    
    # Check if a user owns a file (or is admin).
    @staticmethod
    def verify_file_ownership(file_id, customer_id=None, session_id=None, is_admin=False):
        try:
            with get_db_session() as session:
                file = session.query(UploadedFile).filter_by(file_id=file_id).first()
                if not file:
                    return False
                if is_admin:
                    return True
                return (
                    (customer_id and file.customer_id == customer_id)
                    or (session_id and file.session_id == session_id)
                )
        except Exception:
            return False
    
    # Return summary statistics of a user's files.
    @staticmethod
    def get_file_statistics(customer_id=None):
         
        try:
            with get_db_session() as session:
                if not customer_id:
                    return {"total_files": 0}
                files = session.query(UploadedFile).filter_by(customer_id=customer_id).all()
                return {
                    "total_files": len(files),
                    "files_in_cart": sum(1 for f in files if f.cart_item_id),
                    "files_in_orders": sum(1 for f in files if f.order_item_id),
                    "unassigned_files": sum(1 for f in files if not f.cart_item_id and not f.order_item_id),
                }
        except Exception:
            return {"total_files": 0}
    
    # Clean up orphaned files (not attached to cart or order).
    @staticmethod
    def cleanup_orphaned_files(days_old=30):
        try:
            with get_db_session() as session:
                cutoff = datetime.now() - timedelta(days=days_old)
                orphaned = session.query(UploadedFile).filter(
                    UploadedFile.cart_item_id == None,
                    UploadedFile.order_item_id == None,
                    UploadedFile.uploaded_at < cutoff
                ).all()

                deleted_count = 0
                for file in orphaned:
                    try:
                        # Optionally remove from filesystem if path known
                        session.delete(file)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting orphaned file: {e}")

                return deleted_count
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return 0
        
    # Return upload configuration for frontend display.
    @staticmethod
    def get_file_info():
        return {
            "allowed_extensions": list(FileService.ALLOWED_EXTENSIONS),
            "max_file_size_bytes": FileService.MAX_FILE_SIZE,
            "max_file_size_mb": FileService.MAX_FILE_SIZE / (1024 * 1024),
            "max_files_per_upload": 10,
        }