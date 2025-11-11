"""
app/services/file_service.py
File Service
Business logic for file upload and management

"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from werkzeug.utils import secure_filename 

from app.models import UploadedFile, CartItem, OrderItem
from app.utils.helpers import FileHelper
from app.utils.validators import Validators


class FileService: 
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file extension is allowed."""
        return Validators.validate_file_extension(filename, FileService.ALLOWED_EXTENSIONS)
    
    @staticmethod
    def generate_unique_filename(original_filename):
        """Generate a unique, safe filename."""
        return FileHelper.generate_unique_filename(original_filename)

    @staticmethod
    def get_file_path(filename, customer_id=None, session_id=None):
        """Get file path for storage"""
        if customer_id:
            folder = f"customer_{customer_id}"
        elif session_id:
            folder = f"guest_{session_id}"
        else:
            folder = "general"

        unique_filename = FileService.generate_unique_filename(filename)
        return os.path.join("uploads", folder, unique_filename)
    
    @staticmethod
    def save_file(file, customer_id=None, session_id=None, 
                  cart_item_id=None, order_item_id=None, upload_folder=None):
        """Save uploaded file"""
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
            uploaded_file_model = UploadedFile()
            file_id = uploaded_file_model.create(
                file_url=f"/static/{file_path}",
                original_filename=file.filename,
                customer_id=customer_id,
                session_id=session_id,
                cart_item_id=cart_item_id,
                order_item_id=order_item_id
            )

            # Attach to related item if needed
            if cart_item_id:
                cart_item_model = CartItem()
                cart_item = cart_item_model.get_by_id(cart_item_id)
                if cart_item:
                    cart_item_model.update(cart_item_id, design_file_url=f"/static/{file_path}")

            if order_item_id:
                order_item_model = OrderItem()
                order_item = order_item_model.get_by_id(order_item_id)
                if order_item:
                    order_item_model.update(order_item_id, design_file_url=f"/static/{file_path}")

            # Get the uploaded file record
            uploaded_file = uploaded_file_model.get_by_id(file_id)
            return True, uploaded_file

        except Exception as e:
            return False, f"Failed to save file: {str(e)}"
    

    # Save multiple uploaded files
    @staticmethod
    def save_multiple_files(files, customer_id=None, session_id=None, upload_folder=None): 
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


    # Retrieve file record by ID
    @staticmethod
    def get_file_by_id(file_id): 
        try:
            uploaded_file_model = UploadedFile()
            return uploaded_file_model.get_by_id(file_id)
        except Exception:
            return None
    

    # Fetch all files associated with a user or guest session.
    @staticmethod
    def get_user_files(customer_id=None, session_id=None): 
        try:
            uploaded_file_model = UploadedFile()
            
            if customer_id:
                files = uploaded_file_model.get_by_customer(customer_id)
            elif session_id:
                files = uploaded_file_model.get_by_session(session_id)
            else:
                return []
            
            # Sort by uploaded_at descending
            files.sort(key=lambda x: x.get('uploaded_at') or datetime.now().min, reverse=True)
            return files
        except Exception:
            return []
    

    # Delete a file and its record if user owns it.
    @staticmethod
    def delete_file(file_id, customer_id=None, session_id=None, upload_folder=None): 
        try:
            uploaded_file_model = UploadedFile()
            file = uploaded_file_model.get_by_id(file_id)
            
            if not file:
                return False, "File not found"

            # Ownership validation
            if customer_id and file.get('customer_id') != customer_id:
                return False, "Access denied"
            if session_id and file.get('session_id') != session_id:
                return False, "Access denied"
            if file.get('order_item_id'):
                return False, "Cannot delete file attached to an order"

            # Delete physical file
            try:
                file_path = file['file_url'].replace("/static/", "")
                full_path = os.path.join(upload_folder, file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                print(f"Error deleting file from disk: {e}")

            uploaded_file_model.delete(file_id)
            return True, "File deleted successfully"

        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"
    

    # Check if a user owns a file (or is admin)
    @staticmethod
    def verify_file_ownership(file_id, customer_id=None, session_id=None, is_admin=False): 
        try:
            uploaded_file_model = UploadedFile()
            file = uploaded_file_model.get_by_id(file_id)
            
            if not file:
                return False
            if is_admin:
                return True
            return (
                (customer_id and file.get('customer_id') == customer_id)
                or (session_id and file.get('session_id') == session_id)
            )
        except Exception:
            return False
    

    # Return summary statistics of a user's files.
    @staticmethod
    def get_file_statistics(customer_id=None): 
        try:
            if not customer_id:
                return {"total_files": 0}
            
            uploaded_file_model = UploadedFile()
            files = uploaded_file_model.get_by_customer(customer_id)
            
            return {
                "total_files": len(files),
                "files_in_cart": sum(1 for f in files if f.get('cart_item_id')),
                "files_in_orders": sum(1 for f in files if f.get('order_item_id')),
                "unassigned_files": sum(1 for f in files if not f.get('cart_item_id') and not f.get('order_item_id')),
            }
        except Exception:
            return {"total_files": 0}
    

    # Clean up orphaned files (not attached to cart or order).
    @staticmethod
    def cleanup_orphaned_files(days_old=30, upload_folder='uploads'): 
        """Clean up orphaned files (not attached to cart or order) older than X days"""
        try:
            from datetime import timedelta
            uploaded_file_model = UploadedFile()
            cutoff_date = datetime.now() - timedelta(days=days_old)
            deleted_count = 0
            
            orphaned = uploaded_file_model.get_orphaned_files(cutoff_date)
            
            for file in orphaned:
                # Delete physical file
                try:
                    file_path = file['file_url'].replace("/static/", "")
                    full_path = os.path.join(upload_folder, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting physical file {file['file_id']}: {e}")
                
                # Delete database record
                uploaded_file_model.delete(file['file_id'])
                deleted_count += 1
            
            print(f"Cleaned up {deleted_count} orphaned files")
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