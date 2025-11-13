// ===================================
// DESIGN.JS - Design Page Functionality
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Elements
    // ===================================
    const uploadArea = document.getElementById('upload-area');
    const designInput = document.getElementById('design-input');
    const designOverlay = document.getElementById('design-overlay');
    const designInfo = document.getElementById('design-info');
    const designFilename = document.getElementById('design-filename');
    const removeDesignBtn = document.getElementById('remove-design');
    const addToCartBtn = document.getElementById('add-to-cart-btn');
    const quantityInput = document.getElementById('quantity');
    const addToCartForm = document.getElementById('add-to-cart-form');
    const cartQuantityInput = document.getElementById('cart-quantity');
    const cartDesignUrlInput = document.getElementById('cart-design-url');
    
    // State
    let currentDesign = null;
    let isUploading = false;
    
    // ===================================
    // Drag & Drop
    // ===================================
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        if (!isUploading) {
            uploadArea.classList.add('dragover');
        }
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (isUploading) return;
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
    
    // ===================================
    // File Input
    // ===================================
    designInput.addEventListener('change', function(e) {
        if (isUploading) return;
        
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
    
    // ===================================
    // Upload Click
    // ===================================
    uploadArea.addEventListener('click', function() {
        if (!isUploading) {
            designInput.click();
        }
    });
    
    // ===================================
    // File Upload Handler
    // ===================================
    async function handleFileUpload(file) {
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            showNotification('Please upload an image file (PNG, JPG, GIF, or WEBP)', 'error');
            return;
        }
        
        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            showNotification('File size must be less than 5MB', 'error');
            return;
        }
        
        isUploading = true;
        uploadArea.classList.add('loading');
        
        // Create FormData
        const formData = new FormData();
        formData.append('design', file);
        
        // Get product ID from URL
        const pathParts = window.location.pathname.split('/');
        const productId = pathParts[pathParts.length - 1];
        
        try {
            const response = await fetch(`/products/${productId}/upload-design`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Success!
                currentDesign = result.design;
                displayDesign(result.design);
                showNotification('Design uploaded successfully!', 'success');
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showNotification(error.message || 'Failed to upload design', 'error');
        } finally {
            isUploading = false;
            uploadArea.classList.remove('loading');
        }
    }
    
    // ===================================
    // Display Design
    // ===================================
    function displayDesign(design) {
        // Hide upload area, show design info
        uploadArea.style.display = 'none';
        designInfo.style.display = 'block';
        
        // Update filename
        designFilename.textContent = design.original_filename;
        
        // Show design on product mockup
        if (design.preview_url) {
            // If we have a preview with the design already on the mockup
            const previewImage = document.getElementById('preview-image');
            previewImage.src = design.preview_url;
            designOverlay.innerHTML = '';
        } else {
            // Otherwise, overlay the design on the mockup
            const designImg = document.createElement('img');
            designImg.src = design.design_url;
            designImg.alt = 'Your Design';
            designImg.style.width = '100%';
            designImg.style.height = '100%';
            designImg.style.objectFit = 'contain';
            
            designOverlay.innerHTML = '';
            designOverlay.appendChild(designImg);
        }
        
        // Enable add to cart
        addToCartBtn.disabled = false;
        document.querySelector('.cart-note').textContent = '*Design ready! Choose quantity and add to cart.';
    }
    
    // ===================================
    // Remove Design
    // ===================================
    removeDesignBtn.addEventListener('click', function() {
        if (!confirm('Remove current design?')) {
            return;
        }
        
        // Clear design
        currentDesign = null;
        
        // Reset preview
        const previewImage = document.getElementById('preview-image');
        const pathParts = window.location.pathname.split('/');
        const productId = pathParts[pathParts.length - 1];
        previewImage.src = `/static/images/products/mockups/product_${productId}_mockup.png`;
        previewImage.onerror = function() {
            this.src = '/static/images/products/mockups/default_mockup.png';
        };
        designOverlay.innerHTML = '';
        
        // Show upload area, hide design info
        uploadArea.style.display = 'block';
        designInfo.style.display = 'none';
        
        // Disable add to cart
        addToCartBtn.disabled = true;
        document.querySelector('.cart-note').textContent = '*Please upload a design first';
        
        // Clear file input
        designInput.value = '';
        
        showNotification('Design removed', 'info');
    });
    
    // ===================================
    // Add to Cart
    // ===================================
    addToCartBtn.addEventListener('click', async function() {
        if (!currentDesign) {
            showNotification('Please upload a design first', 'warning');
            return;
        }
        
        const quantity = parseInt(quantityInput.value);
        
        if (quantity < 1 || quantity > 100) {
            showNotification('Quantity must be between 1 and 100', 'warning');
            return;
        }
        
        // Set form values
        cartQuantityInput.value = quantity;
        cartDesignUrlInput.value = currentDesign.design_url;
        
        // Disable button
        addToCartBtn.disabled = true;
        addToCartBtn.textContent = 'Adding...';
        
        try {
            // Submit form via AJAX
            const formData = new FormData(addToCartForm);
            const data = Object.fromEntries(formData.entries());
            
            const response = await fetch(addToCartForm.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showNotification('Added to cart!', 'success');
                
                // Update cart count
                if (window.updateCartCount) {
                    updateCartCount();
                }
                
                // Redirect to cart after 1 second
                setTimeout(() => {
                    window.location.href = '/cart/view';
                }, 1000);
            } else {
                throw new Error(result.error || 'Failed to add to cart');
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            showNotification(error.message || 'Failed to add to cart', 'error');
            addToCartBtn.disabled = false;
            addToCartBtn.textContent = 'Add to Cart';
        }
    });
    
    // ===================================
    // Quantity Validation
    // ===================================
    quantityInput.addEventListener('change', function() {
        let value = parseInt(this.value);
        
        if (isNaN(value) || value < 1) {
            this.value = 1;
        } else if (value > 100) {
            this.value = 100;
        }
    });
    
});

// ===================================
// Notification Function
// ===================================
function showNotification(message, type = 'info') {
    let container = document.querySelector('.flash-messages');
    
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.innerHTML = `
        ${message}
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(400px)';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}