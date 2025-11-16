"""
app/services/design_service.py - FIXED VERSION
Design Service with proper preview generation
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename

from app.models import Product, UploadedFile
from app.utils.image_helpers import ImageHelper
from app.utils.image_processor import ImageProcessor
from app.utils.helpers import FileHelper


class DesignService:
    """Service for handling design customization"""
    
    DEFAULT_SCALE = 0.40
    DEFAULT_X = 0.5
    DEFAULT_Y = 0.5
    
    @staticmethod
    def process_design_upload(file, product_id, customer_id=None, session_id=None):
        """
        Process uploaded design file and create preview using product mockup.
        Returns design URL and preview URL
        """

        if not file or file.filename == '':
            return False, "No file provided"

        if not FileHelper.get_file_extension(file.filename):
            return False, "Invalid file type"

        try:
            # 1. Setup directories
            designs_dir = "app/static/images/designs"
            previews_dir = "app/static/images/previews"

            os.makedirs(designs_dir, exist_ok=True)
            os.makedirs(previews_dir, exist_ok=True)

            # 2. Generate filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)

            design_filename = f"design_{product_id}_{timestamp}_{original_filename}"
            preview_filename = f"preview_{product_id}_{timestamp}.jpg"

            design_path = os.path.join(designs_dir, design_filename)
            preview_path = os.path.join(previews_dir, preview_filename)

            # 3. Save original design
            file.save(design_path)

            # 4. Validate image
            is_valid, error_msg = ImageProcessor.validate_image(design_path)
            if not is_valid:
                os.remove(design_path)
                return False, error_msg

            # 5. Get product mockup
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product:
                os.remove(design_path)
                return False, "Product not found"

            # Get mockup path (absolute)
            mockup_url = ImageHelper.get_mockup_url(product_id)
            # Convert URL to file path
            if mockup_url.startswith('/static/'):
                mockup_relative = mockup_url[8:]  # Remove '/static/'
            else:
                mockup_relative = mockup_url.lstrip('/')
            
            mockup_path = os.path.join('app', 'static', mockup_relative)

            # 6. Generate preview with mockup
            preview_url = None
            if os.path.exists(mockup_path):
                success, msg = ImageProcessor.create_preview_with_mockup(
                    design_path,
                    mockup_path,
                    preview_path,
                    design_scale=DesignService.DEFAULT_SCALE,
                    design_x=DesignService.DEFAULT_X,
                    design_y=DesignService.DEFAULT_Y
                )

                if success:
                    preview_url = f"/static/images/previews/{preview_filename}"
                else:
                    print(f"Preview generation failed: {msg}")
                    # Continue without preview
            else:
                print(f"Mockup not found at: {mockup_path}")

            # 7. Save to database
            uploaded_file_model = UploadedFile()
            file_id = uploaded_file_model.create(
                file_url=f"/static/images/designs/{design_filename}",
                original_filename=original_filename,
                customer_id=customer_id,
                session_id=session_id
            )

            # 8. Get image metadata
            image_info = ImageProcessor.get_image_info(design_path)

            # 9. Return complete data
            return True, {
                "file_id": file_id,
                "design_url": f"/static/images/designs/{design_filename}",
                "preview_url": preview_url,  # This is the key field!
                "original_filename": original_filename,
                "image_info": image_info,
                "product_id": product_id
            }

        except Exception as e:
            import traceback
            print(f"Design upload error: {str(e)}")
            print(traceback.format_exc())
            return False, f"Failed to process design: {str(e)}"