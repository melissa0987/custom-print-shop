"""
app/utils/image_helpers.py
Helper functions for managing product and design images
"""

import os
from pathlib import Path

from flask import current_app

class ImageHelper:
    """Helper class for managing images"""
    
    # Default image paths 
    DEFAULT_PRODUCT_IMAGE = '/images/products/default.png'
    PRODUCT_IMAGES_DIR = 'static/images/products'
    MOCKUPS_DIR = 'static/images/products/mockups'
    DESIGNS_DIR = 'static/images/products/designs'

    PRODUCT_IMAGE_MAP = {
        'mug': 'images/products/mug.png',
        'shirt': 'images/products/shirt.png',
        'drawstring bag': 'images/products/drawstring-bag.png',
        'tote': 'images/products/tote.png',
        'tumbler': 'images/products/tumbler.png'
    } 

    
    @staticmethod
    def get_product_image_url(product_id, product_name=None):
         
        base_dir = ImageHelper.PRODUCT_IMAGES_DIR
        
        if product_id:
            for ext in ['png', 'jpg', 'jpeg']:
                filename = f"product_{product_id}.{ext}"
                path = os.path.join(current_app.root_path, base_dir, filename)
                if os.path.exists(path):
                    return f"images/products/{filename}"
                
        if product_id:
            if product_id in [1, 2]:
                return ImageHelper.PRODUCT_IMAGE_MAP['mug']
            elif product_id in [3, 4]:
                return ImageHelper.PRODUCT_IMAGE_MAP['tumbler']
            elif product_id == 5:
                return ImageHelper.PRODUCT_IMAGE_MAP['tote']
            elif product_id == 6:
                return ImageHelper.PRODUCT_IMAGE_MAP['drawstring bag']
            elif product_id in range(7, 11):
                return ImageHelper.PRODUCT_IMAGE_MAP['shirt']
            
        
         # --- 2. Keyword mapping from product_name ---
        if product_name:
            name_lower = product_name.lower()
            for key, path in ImageHelper.PRODUCT_IMAGE_MAP.items():
                if key in name_lower:
                    return path

        # --- 3. Fallback default ---
        return ImageHelper.DEFAULT_PRODUCT_IMAGE
    
    
    
    @staticmethod
    def get_mockup_url(product_id):
        """Reuse product images as mockups."""
        url = ImageHelper.get_product_image_url(product_id)

        if not url.startswith("/static/"):
            url = f"/static/{url.lstrip('/')}"

        return url
        
    @staticmethod
    def ensure_directories():
        """Ensure all required image directories exist"""
        directories = [
            ImageHelper.PRODUCT_IMAGES_DIR,
            ImageHelper.MOCKUPS_DIR,
            ImageHelper.DESIGNS_DIR,
            '/static/images/uploads/previews'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_design_thumbnail_url(design_url, size='small'):
        """
        Get thumbnail URL for a design
        For now, returns the original design URL
        Future: Could generate actual thumbnails
        """
        if not design_url:
            return None
        
        # For now, just return the design URL
        # In production, you might want to generate thumbnails
        return design_url
    
    @staticmethod
    def validate_image_file(filename):
        """Check if file is a valid image"""
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
        ext = os.path.splitext(filename)[1].lower()
        return ext in allowed_extensions


# Example usage in your product service or routes:
"""
# In product_service.py or products route:

from app.utils.image_helpers import ImageHelper

# When fetching products:
product_data = {
    'product_id': product['product_id'],
    'product_name': product['product_name'],
    'image_url': ImageHelper.get_product_image_url(
        product['product_id'], 
        product['product_name']
    ),
    ...
}

# For mockups in design page:
mockup_url = ImageHelper.get_mockup_url(product_id)
"""