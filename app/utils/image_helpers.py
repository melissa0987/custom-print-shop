"""
app/utils/image_helpers.py
Helper functions for managing product and design images
"""

import os
from pathlib import Path

class ImageHelper:
    """Helper class for managing images"""
    
    # Default image paths
    DEFAULT_PRODUCT_IMAGE = '/static/images/products/default.png'
    PRODUCT_IMAGES_DIR = 'app/static/images/products'
    MOCKUPS_DIR = 'app/static/images/products/mockups'
    DESIGNS_DIR = 'uploads/designs'
    
    @staticmethod
    def get_product_image_url(product_id, product_name=None):
        """
        Get product image URL, returns default if not found
        Checks for:
        1. product_{id}.png
        2. product_{id}.jpg
        3. {slugified_name}.png
        4. Default image
        """
        base_path = ImageHelper.PRODUCT_IMAGES_DIR
        
        # Try with product_id
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            img_path = f"{base_path}/product_{product_id}{ext}"
            if os.path.exists(img_path):
                return f"/static/images/products/product_{product_id}{ext}"
        
        # Try with slugified name if provided
        if product_name:
            from app.utils.helpers import StringHelper
            slug = StringHelper.slugify(product_name)
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                img_path = f"{base_path}/{slug}{ext}"
                if os.path.exists(img_path):
                    return f"/static/images/products/{slug}{ext}"
        
        # Return default
        return ImageHelper.DEFAULT_PRODUCT_IMAGE
    
    @staticmethod
    def get_mockup_url(product_id):
        """Get product mockup for design preview"""
        mockup_path = f"{ImageHelper.MOCKUPS_DIR}/product_{product_id}_mockup.png"
        
        if os.path.exists(mockup_path):
            return f"/static/images/products/mockups/product_{product_id}_mockup.png"
        
        # Return default mockup
        return "/static/images/products/mockups/default_mockup.png"
    
    @staticmethod
    def ensure_directories():
        """Ensure all required image directories exist"""
        directories = [
            ImageHelper.PRODUCT_IMAGES_DIR,
            ImageHelper.MOCKUPS_DIR,
            ImageHelper.DESIGNS_DIR,
            'uploads/previews'
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