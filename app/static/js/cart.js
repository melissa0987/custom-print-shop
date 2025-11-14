// ===================================
// CART.JS - Cart Functionality
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Add to Cart with AJAX
    // ===================================
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    
    addToCartForms.forEach(form => {
        form.addEventListener('submit', async function(e) {
            // Only prevent default if we want AJAX behavior
            // For now, let's use AJAX for better UX
            e.preventDefault();
            
            const button = form.querySelector('.btn-add-cart');
            const originalText = button.textContent;
            
            // Get form data
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            // Disable button and show loading
            button.disabled = true;
            button.classList.add('loading');
            button.textContent = '';
            
            try {
                const response = await fetch('/cart/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // Success!
                    button.classList.remove('loading');
                    button.classList.add('success');
                    button.textContent = 'Added!';
                    
                    // Update cart count
                    updateCartCount();
                    
                    // Show success notification
                    showNotification('Item added to cart!', 'success');
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {
                        button.classList.remove('success');
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                } else {
                    // Error
                    throw new Error(result.error || 'Failed to add to cart');
                }
            } catch (error) {
                console.error('Error:', error);
                button.classList.remove('loading');
                button.textContent = originalText;
                button.disabled = false;
                showNotification(error.message || 'Failed to add to cart', 'error');
            }
        });
    });
    
    // ===================================
    // Update Cart Count
    // ===================================
    async function updateCartCount() {
        try {
            const response = await fetch('/cart/count');
            const data = await response.json();
            
            const cartCountBadges = document.querySelectorAll('.cart-count');
            const cartLinks = document.querySelectorAll('.cart-link');
            
            if (data.count > 0) {
                // Update or create badge
                cartLinks.forEach(link => {
                    let badge = link.querySelector('.cart-count');
                    if (!badge) {
                        badge = document.createElement('span');
                        badge.className = 'cart-count';
                        link.appendChild(badge);
                    }
                    badge.textContent = data.count;
                    badge.classList.add('updating');
                    setTimeout(() => badge.classList.remove('updating'), 500);
                });
            } else {
                // Remove badge if count is 0
                cartCountBadges.forEach(badge => badge.remove());
            }
        } catch (error) {
            console.error('Error updating cart count:', error);
        }
    }
    
    // ===================================
    // Remove Cart Item Confirmation
    // ===================================
    const removeButtons = document.querySelectorAll('form[action*="/cart/remove/"]');
    
    removeButtons.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmed = confirm('Remove this item from cart?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
    
    // ===================================
    // Clear Cart Confirmation
    // ===================================
    const clearCartForms = document.querySelectorAll('form[action*="/cart/clear"]');
    
    clearCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmed = confirm('Clear all items from cart?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
    
    // ===================================
    // Notification System
    // ===================================
    function showNotification(message, type = 'info') {
        // Check if there's already a flash messages container
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
            <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
        `;
        
        container.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    // Make showNotification globally available
    window.showNotification = showNotification;
    
    // ===================================
    // Initialize Cart Count on Page Load
    // ===================================
    updateCartCount();


    // ===================================
    // Cart Quantity Updates
    // ===================================
    document.querySelectorAll('.btn-update').forEach(button => {
        button.addEventListener('click', async (e) => {
            const itemId = e.target.dataset.itemId;
            const itemRow = e.target.closest('.cart-item');
            const qtyInput = itemRow.querySelector('.quantity-input');
            let newQty = parseInt(qtyInput.value);

            if (isNaN(newQty) || newQty < 1) {
                showNotification('Quantity must be at least 1', 'warning');
                qtyInput.value = 1;
                return;
            }

            try {
                const response = await fetch(`/cart/update/${itemId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ quantity: newQty })
                });

                const result = await response.json();

                if (response.ok) {
                    // Update line total
                    const lineTotalElem = itemRow.querySelector('.line-total');
                    const updatedItem = result.cart.items.find(i => i.cart_item_id == itemId);
                    if (lineTotalElem && updatedItem) {
                        lineTotalElem.textContent = updatedItem.line_total_formatted;
                    }

                    // Update cart summary totals
                    const subtotalElem = document.querySelector('.cart-summary .summary-row:nth-child(1) span:last-child');
                    const taxElem = document.querySelector('.cart-summary .summary-row:nth-child(2) span:last-child');
                    const totalElem = document.querySelector('.cart-summary .summary-row.total span:last-child strong');

                    if (subtotalElem) subtotalElem.textContent = result.cart.subtotal_formatted;
                    if (taxElem) taxElem.textContent = result.cart.tax_formatted;
                    if (totalElem) totalElem.textContent = result.cart.cart_total_formatted;

                    showNotification('Cart updated successfully', 'success');
                } else {
                    showNotification(result.error || 'Failed to update item', 'error');
                }
            } catch (err) {
                console.error(err);
                showNotification('Error updating cart item', 'error');
            }
        });
    });

     
    
});
