"""
setup_mockups.py
Script to create necessary directories and a default mockup image
Run this once to set up the project structure
"""

import os
from PIL import Image, ImageDraw, ImageFont

# Create directories
directories = [
    'app/static/images/products/mockups',
    'uploads/designs',
    'uploads/previews'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"✓ Created directory: {directory}")

# Create a default mockup image (white mug)
def create_default_mockup():
    """Create a simple default product mockup"""
    # Create 800x800 image
    width, height = 800, 800
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple mug shape
    # Body of mug (rectangle with rounded corners)
    mug_left = 200
    mug_top = 200
    mug_right = 600
    mug_bottom = 600
    
    # Draw main body (white with gray outline)
    draw.rounded_rectangle(
        [(mug_left, mug_top), (mug_right, mug_bottom)],
        radius=40,
        fill='white',
        outline='#cccccc',
        width=3
    )
    
    # Draw handle
    handle_left = mug_right - 20
    handle_top = mug_top + 100
    handle_right = mug_right + 80
    handle_bottom = mug_bottom - 100
    
    draw.arc(
        [(handle_left, handle_top), (handle_right, handle_bottom)],
        start=270,
        end=90,
        fill='#cccccc',
        width=20
    )
    
    # Add subtle shadow
    shadow_offset = 10
    draw.ellipse(
        [(mug_left + shadow_offset, mug_bottom), 
         (mug_right + shadow_offset, mug_bottom + 40)],
        fill='#e0e0e0'
    )
    
    # Add text "Your Design Here" in the center
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
    
    text = "Your Design Here"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    draw.text((text_x, text_y), text, fill='#cccccc', font=font)
    
    # Save
    output_path = 'app/static/images/products/mockups/default_mockup.png'
    img.save(output_path, 'PNG')
    print(f"✓ Created default mockup: {output_path}")

# Create mockup
create_default_mockup()

print("\n✓ Setup complete!")
print("\nNext steps:")
print("1. Run this script: python setup_mockups.py")
print("2. Add product-specific mockups to app/static/images/products/mockups/")
print("3. Name them as: product_<product_id>_mockup.png")
print("4. Start your Flask app and test the design feature!")