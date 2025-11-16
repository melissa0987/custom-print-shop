// app/static/js/design.js
// Complete design upload and preview system

document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('upload-area');
    const designInput = document.getElementById('design-input');
    const designInfo = document.getElementById('design-info');
    const designFilename = document.getElementById('design-filename');
    const removeDesignBtn = document.getElementById('remove-design');
    const addToCartBtn = document.getElementById('add-to-cart-btn');
    const previewImage = document.getElementById('preview-image');
    const designOverlay = document.getElementById('design-overlay');
    const quantityInput = document.getElementById('quantity');
    
    let uploadedDesignUrl = null;
    let uploadedPreviewUrl = null;

    // Make upload area clickable
    uploadArea.addEventListener('click', () => designInput.click());

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // File input change handler
    designInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Remove design handler
    removeDesignBtn.addEventListener('click', () => {
        resetDesign();
    });

    // Add to cart handler
    addToCartBtn.addEventListener('click', () => {
        addToCart();
    });

    // Handle file upload
    async function handleFileUpload(file) {
        // Validate file
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('Please upload a valid image file (PNG, JPG, GIF, WEBP)');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return;
        }

        // Show loading state
        uploadArea.style.display = 'none';
        designInfo.style.display = 'block';
        designFilename.textContent = 'Uploading...';
        addToCartBtn.disabled = true;
        addToCartBtn.classList.add('loading');

        try {
            // Get product ID from the page
            const productId = getProductIdFromPage();
            
            // Upload the design
            const formData = new FormData();
            formData.append('design', file);

            const response = await fetch(`/products/${productId}/upload-design`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();
            
            // Store the uploaded URLs
            uploadedDesignUrl = result.design.design_url;
            uploadedPreviewUrl = result.design.preview_url;

            // Update UI
            designFilename.textContent = file.name;
            
            // Show preview if available
            if (uploadedPreviewUrl) {
                updatePreview(uploadedPreviewUrl);
            } else {
                // Fallback: show design directly on overlay
                showDesignOverlay(uploadedDesignUrl);
            }

            // Enable add to cart
            addToCartBtn.disabled = false;
            addToCartBtn.classList.remove('loading');
            document.querySelector('.cart-note').style.display = 'none';

        } catch (error) {
            console.error('Upload error:', error);
            alert('Failed to upload design. Please try again.');
            resetDesign();
        }
    }

    // Update preview with the generated mockup
    function updatePreview(previewUrl) {
        previewImage.src = previewUrl;
        designOverlay.innerHTML = ''; // Clear overlay since preview is already composite
    }

    // Show design on overlay (fallback)
    function showDesignOverlay(designUrl) {
        designOverlay.innerHTML = `<img src="${designUrl}" alt="Design Preview" style="max-width: 100%; max-height: 100%;">`;
    }

    // Reset design state
    function resetDesign() {
        uploadedDesignUrl = null;
        uploadedPreviewUrl = null;
        designInput.value = '';
        uploadArea.style.display = 'block';
        designInfo.style.display = 'none';
        designOverlay.innerHTML = '';
        addToCartBtn.disabled = true;
        document.querySelector('.cart-note').style.display = 'block';
        
        // Reset preview to product mockup
        const productId = getProductIdFromPage();
        previewImage.src = `/static/images/products/mockups/product_${productId}_mockup.png`;
        previewImage.onerror = function() {
            this.src = '/static/images/products/mockups/default.png';
        };
    }

    // Add to cart with design
    async function addToCart() {
        if (!uploadedDesignUrl) {
            alert('Please upload a design first');
            return;
        }

        const productId = getProductIdFromPage();
        const quantity = parseInt(quantityInput.value);

        if (quantity < 1) {
            alert('Quantity must be at least 1');
            return;
        }

        // Show loading
        addToCartBtn.disabled = true;
        addToCartBtn.textContent = 'Adding...';

        try {
            const response = await fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    design_file_url: uploadedDesignUrl
                })
            });

            const result = await response.json();

            if (response.ok) {
                // Update cart count in header
                updateCartCount(result.cart.total_items);
                
                // Show success message
                showSuccessMessage('Added to cart successfully!');
                
                // Reset for next design
                setTimeout(() => {
                    resetDesign();
                    addToCartBtn.textContent = 'Add to Cart';
                }, 1500);
            } else {
                throw new Error(result.error || 'Failed to add to cart');
            }

        } catch (error) {
            console.error('Add to cart error:', error);
            alert('Failed to add to cart: ' + error.message);
            addToCartBtn.disabled = false;
            addToCartBtn.textContent = 'Add to Cart';
        }
    }

    // Helper: Get product ID from page
    function getProductIdFromPage() {
        // Extract from URL or hidden input
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    // Helper: Update cart count in header
    function updateCartCount(count) {
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            cartCountElement.textContent = count;
            if (count > 0) {
                cartCountElement.style.display = 'inline-block';
            }
        }
    }

    // Helper: Show success message
    function showSuccessMessage(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        successDiv.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => successDiv.remove(), 300);
        }, 3000);
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);