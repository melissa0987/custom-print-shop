// ===================================
// MAIN.JS - Interactive Features
// ===================================

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Flash Messages Auto-Dismiss
    // ===================================
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateX(400px)';
            setTimeout(() => message.remove(), 300);
        }, 5000); // Auto-dismiss after 5 seconds
    });
    
    // ===================================
    // FAQ Accordion
    // ===================================
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach(question => {
        question.addEventListener('click', function() {
            const answer = this.nextElementSibling;
            const isOpen = answer.style.maxHeight && answer.style.maxHeight !== '0px';
            
            // Close all other answers
            document.querySelectorAll('.faq-answer').forEach(a => {
                a.style.maxHeight = null;
            });
            
            // Remove active class from all questions
            faqQuestions.forEach(q => q.classList.remove('active'));
            
            // Toggle current answer
            if (!isOpen) {
                answer.style.maxHeight = answer.scrollHeight + 'px';
                this.classList.add('active');
            }
        });
    });
    
    
    // ===================================
    // Form Validation
    // ===================================
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showNotification('Please fill in all required fields', 'warning');
            }
        });
    });
    
    function validateForm(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.style.borderColor = 'var(--danger)';
                isValid = false;
            } else {
                field.style.borderColor = 'var(--border-color)';
            }
        });
        
        return isValid;
    }
    
    // ===================================
    // Product Image Gallery (if implemented)
    // ===================================
    const productThumbnails = document.querySelectorAll('.product-thumbnail');
    const mainProductImage = document.querySelector('.main-product-image');
    
    productThumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            if (mainProductImage) {
                mainProductImage.src = this.dataset.fullImage;
                
                // Update active thumbnail
                productThumbnails.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
    
    // ===================================
    // Smooth Scroll for Anchor Links
    // ===================================
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // ===================================
    // Loading State for Forms
    // ===================================
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const form = this.closest('form');
            if (form && form.checkValidity()) {
                this.disabled = true;
                this.textContent = 'Processing...';
                
                // Re-enable after 5 seconds (safety measure)
                setTimeout(() => {
                    this.disabled = false;
                    this.textContent = this.dataset.originalText || 'Submit';
                }, 5000);
            }
        });
        
        // Store original text
        button.dataset.originalText = button.textContent;
    });
    
    // ===================================
    // Notification System
    // ===================================
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `flash-message flash-${type}`;
        notification.innerHTML = `
            ${message}
            <button onclick="this.parentElement.remove()">&times;</button>
        `;
        
        let container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            document.body.appendChild(container);
        }
        
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
    // Mobile Navigation Toggle
    // ===================================
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // ===================================
    // Lazy Loading Images
    // ===================================
    const lazyImages = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
    
    // ===================================
    // Price Formatting
    // ===================================
    function formatPrice(price) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(price);
    }
    
    window.formatPrice = formatPrice;
    
    // ===================================
    // Confirmation Dialogs
    // ===================================
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.dataset.confirm || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // ===================================
    // Add to Cart Animation
    // ===================================
    const addToCartButtons = document.querySelectorAll('.btn-add-cart, .btn-add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Only animate if not inside a form (or handle form separately)
            if (!this.closest('form')) {
                this.classList.add('adding');
                setTimeout(() => {
                    this.classList.remove('adding');
                }, 1000);
            }
        });
    });
    
    // ===================================
    // Search Functionality
    // ===================================
    const searchInput = document.querySelector('#search-input');
    const searchForm = document.querySelector('#search-form');
    
    if (searchInput && searchForm) {
        searchInput.addEventListener('input', function() {
            if (this.value.length < 2) {
                // Don't search for very short queries
                return;
            }
            
            // Debounce search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 500);
        });
    }
    
    function performSearch(query) {
        // Implement AJAX search if needed
        console.log('Searching for:', query);
    }
    
    // ===================================
    // Print Functionality
    // ===================================
    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    });
    
    // ===================================
    // Copy to Clipboard
    // ===================================
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                showNotification('Copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy:', err);
                showNotification('Failed to copy', 'error');
            });
        });
    });
    
    // ===================================
    // Back to Top Button
    // ===================================
    const backToTopButton = document.querySelector('#back-to-top');
    
    if (backToTopButton) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                backToTopButton.style.display = 'flex';
            } else {
                backToTopButton.style.display = 'none';
            }
        });
        
        backToTopButton.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
    
    // ===================================
    // Console Welcome Message
    // ===================================
    console.log(
        '%cPrintCraft',
        'font-size: 20px; font-weight: bold; color: #667eea;'
    );
    console.log(
        '%cCustom Printing Made Easy',
        'font-size: 14px; color: #764ba2;'
    );
    
});

// ===================================
// Utility Functions (Global)
// ===================================

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export utilities
window.utils = {
    debounce,
    throttle
};