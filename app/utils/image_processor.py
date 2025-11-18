"""
app/utils/image_processor.py
Image Processing Utility
Handles image validation, resizing, optimization, and mockup overlay
"""

from PIL import Image, ImageDraw, ImageFilter
import os
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing utilities for design uploads"""
    
    # Supported formats
    ALLOWED_FORMATS = {'PNG', 'JPEG', 'JPG', 'GIF', 'WEBP'}
    
    # Maximum dimensions for uploaded designs
    MAX_DESIGN_WIDTH = 2000
    MAX_DESIGN_HEIGHT = 2000
    
    # Preview dimensions
    PREVIEW_WIDTH = 800
    PREVIEW_HEIGHT = 800
    
    @staticmethod
    def validate_image(file_path):
        """
        Validate that the file is a valid image
        Returns (is_valid, error_message)
        """
        try:
            with Image.open(file_path) as img:
                # Check format
                if img.format not in ImageProcessor.ALLOWED_FORMATS:
                    return False, f"Format {img.format} not supported. Allowed: {', '.join(ImageProcessor.ALLOWED_FORMATS)}"
                
                # Check dimensions
                width, height = img.size
                if width > ImageProcessor.MAX_DESIGN_WIDTH or height > ImageProcessor.MAX_DESIGN_HEIGHT:
                    return False, f"Image too large. Maximum size: {ImageProcessor.MAX_DESIGN_WIDTH}x{ImageProcessor.MAX_DESIGN_HEIGHT}px"
                
                # Check if image can be loaded
                img.verify()
                
                return True, "Valid image"
                
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    @staticmethod
    def optimize_design(input_path, output_path, max_width=None, max_height=None):
        """
        Optimize and resize design image
        Maintains aspect ratio
        """
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    else:
                        background.paste(img)
                    img = background
                
                # Resize if needed
                if max_width or max_height:
                    max_width = max_width or ImageProcessor.MAX_DESIGN_WIDTH
                    max_height = max_height or ImageProcessor.MAX_DESIGN_HEIGHT
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                
                return True, "Image optimized successfully"
                
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return False, f"Failed to optimize image: {str(e)}"
    
    @staticmethod
    def create_preview_with_mockup(design_path, mockup_path, output_path, 
                                   design_scale=0.5, design_x=0.5, design_y=0.5):
        
        try:
            # Open mockup
            with Image.open(mockup_path) as mockup:
                mockup = mockup.convert('RGBA')
                mockup_width, mockup_height = mockup.size
                
                # Open design
                with Image.open(design_path) as design:
                    design = design.convert('RGBA')
                    
                    # Calculate design size (maintain aspect ratio)
                    max_design_width = int(mockup_width * design_scale)
                    max_design_height = int(mockup_height * design_scale)
                    
                    # Resize design while maintaining aspect ratio
                    design.thumbnail((max_design_width, max_design_height), Image.Resampling.LANCZOS)
                    design_width, design_height = design.size
                    
                    # Calculate position to center the design
                    x = int((mockup_width - design_width) * design_x)
                    y = int((mockup_height - design_height) * design_y)
                    
                    # Create a copy of mockup to paste design onto
                    preview = mockup.copy()
                    preview.paste(design, (x, y), design)
                    
                    # Convert to RGB for JPEG
                    preview = preview.convert('RGB')
                    
                    # Resize preview if needed
                    if mockup_width > ImageProcessor.PREVIEW_WIDTH:
                        preview.thumbnail((ImageProcessor.PREVIEW_WIDTH, ImageProcessor.PREVIEW_HEIGHT), 
                                        Image.Resampling.LANCZOS)
                    
                    # Save preview
                    preview.save(output_path, 'JPEG', quality=90, optimize=True)
                    
                    return True, "Preview created successfully"
                    
        except Exception as e:
            logger.error(f"Error creating preview: {str(e)}")
            return False, f"Failed to create preview: {str(e)}"
    
    @staticmethod
    def get_image_info(file_path):
        """Get image dimensions and format"""
        try:
            with Image.open(file_path) as img:
                return {
                    'width': img.size[0],
                    'height': img.size[1],
                    'format': img.format,
                    'mode': img.mode
                }
        except Exception as e:
            logger.error(f"Error getting image info: {str(e)}")
            return None
    
    @staticmethod
    def create_thumbnail(input_path, output_path, size=(200, 200)):
        """Create a thumbnail of the image"""
        try:
            with Image.open(input_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(output_path, 'JPEG', quality=85)
                return True, "Thumbnail created"
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return False, str(e)