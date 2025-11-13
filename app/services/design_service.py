"""
app/services/design_service.py
Design Service
Business logic for design customization and preview generation
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename

from app.models import Product, UploadedFile
from app.utils.image_processor import ImageProcessor
from app.utils.helpers import FileHelper


class DesignService:
    """Service for handling design customization"""
    
    # Default design positioning (centered)
    DEFAULT_SCALE = 0.5  # 50% of mockup size
    DEFAULT_X = 0.5      # Centered horizontally
    DEFAULT_Y = 0.5      # Centered vertically
    
    @staticmethod
    def get_product_mockup_path(product_id):
        """
        Get the path to the product mockup image
        For now, returns a default path
        """
        # TODO: Store mockup paths in database with products
        mockup_filename = f"product_{product_id}_mockup.png"
        mockup_path = os.path.join('app', 'static', 'images', 'products', 'mockups', mockup_filename)
        
        # If specific mockup doesn't exist, use default
        if not os.path.exists(mockup_path):
            mockup_path = os.path.join('app', 'static', 'images', 'products', 'mockups', 'default_mockup.png')
        
        return mockup_path
    
    @staticmethod
    def process_design_upload(file, product_id, customer_id=None, session_id=None, upload_folder='uploads'):
        """
        Process uploaded design file and create preview
        Returns (success, result_dict_or_error_message)
        """
        if not file or file.filename == '':
            return False, "No file provided"
        
        # Validate file extension
        if not FileHelper.get_file_extension(file.filename):
            return False, "Invalid file type"
        
        try:
            # Create necessary directories
            designs_dir = os.path.join(upload_folder, 'designs')
            previews_dir = os.path.join(upload_folder, 'previews')
            os.makedirs(designs_dir, exist_ok=True)
            os.makedirs(previews_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            base_name = os.path.splitext(original_filename)[0]
            
            # Save original file temporarily
            temp_filename = f"temp_{timestamp}_{original_filename}"
            temp_path = os.path.join(designs_dir, temp_filename)
            file.save(temp_path)
            
            # Validate image
            is_valid, error_msg = ImageProcessor.validate_image(temp_path)
            if not is_valid:
                os.remove(temp_path)
                return False, error_msg
            
            # Generate final filenames
            design_filename = f"design_{product_id}_{timestamp}_{original_filename}"
            preview_filename = f"preview_{product_id}_{timestamp}.jpg"
            
            design_path = os.path.join(designs_dir, design_filename)
            preview_path = os.path.join(previews_dir, preview_filename)
            
            # Optimize design image
            success, msg = ImageProcessor.optimize_design(temp_path, design_path)
            if not success:
                os.remove(temp_path)
                return False, msg
            
            # Remove temp file
            os.remove(temp_path)
            
            # Get product mockup
            mockup_path = DesignService.get_product_mockup_path(product_id)
            
            # Create preview with design on mockup
            if os.path.exists(mockup_path):
                success, msg = ImageProcessor.create_preview_with_mockup(
                    design_path,
                    mockup_path,
                    preview_path,
                    design_scale=DesignService.DEFAULT_SCALE,
                    design_x=DesignService.DEFAULT_X,
                    design_y=DesignService.DEFAULT_Y
                )
                
                if not success:
                    # Preview creation failed, but design is saved
                    preview_url = None
                else:
                    preview_url = f"/static/uploads/previews/{preview_filename}"
            else:
                # No mockup available, just show the design
                preview_url = f"/static/uploads/designs/{design_filename}"
            
            # Save to database
            uploaded_file_model = UploadedFile()
            file_id = uploaded_file_model.create(
                file_url=f"/static/uploads/designs/{design_filename}",
                original_filename=original_filename,
                customer_id=customer_id,
                session_id=session_id
            )
            
            # Get image info
            image_info = ImageProcessor.get_image_info(design_path)
            
            return True, {
                'file_id': file_id,
                'design_url': f"/static/uploads/designs/{design_filename}",
                'preview_url': preview_url,
                'original_filename': original_filename,
                'image_info': image_info
            }
            
        except Exception as e:
            return False, f"Failed to process design: {str(e)}"
    
    @staticmethod
    def get_design_preview(design_url, product_id):
        """
        Get or generate preview for a design on a product
        """
        try:
            # Extract design filename from URL
            design_filename = os.path.basename(design_url)
            design_path = os.path.join('uploads', 'designs', design_filename)
            
            # Check if preview already exists
            preview_filename = f"preview_{product_id}_{design_filename.replace('.jpg', '.jpg')}"
            preview_path = os.path.join('uploads', 'previews', preview_filename)
            
            if os.path.exists(preview_path):
                return True, f"/static/uploads/previews/{preview_filename}"
            
            # Generate new preview
            mockup_path = DesignService.get_product_mockup_path(product_id)
            
            if not os.path.exists(design_path):
                return False, "Design file not found"
            
            if not os.path.exists(mockup_path):
                return False, "Mockup not available"
            
            success, msg = ImageProcessor.create_preview_with_mockup(
                design_path,
                mockup_path,
                preview_path,
                design_scale=DesignService.DEFAULT_SCALE,
                design_x=DesignService.DEFAULT_X,
                design_y=DesignService.DEFAULT_Y
            )
            
            if success:
                return True, f"/static/uploads/previews/{preview_filename}"
            else:
                return False, msg
                
        except Exception as e:
            return False, f"Failed to generate preview: {str(e)}"
    
    @staticmethod
    def validate_design_for_product(design_id, product_id):
        """
        Validate that a design is suitable for a product
        Future: Check dimensions, color mode, etc.
        """
        # For now, just check if both exist
        uploaded_file_model = UploadedFile()
        design = uploaded_file_model.get_by_id(design_id)
        
        if not design:
            return False, "Design not found"
        
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product:
            return False, "Product not found"
        
        return True, "Design is valid for product"