/**
 * FlashFlow - Card Carousel Design System
 * Main JavaScript File
 */

// ============================================
// CAROUSEL FUNCTIONALITY
// ============================================

/**
 * Scroll carousel left or right
 * @param {string} id - Carousel ID
 * @param {number} direction - -1 for left, 1 for right
 */
function scrollCarousel(id, direction) {
    const carousel = document.getElementById(id + '-carousel');
    if (!carousel) return;

    const scrollAmount = 336; // card width (320px) + gap (16px)
    carousel.scrollBy({
        left: direction * scrollAmount,
        behavior: 'smooth'
    });
}

/**
 * Update scroll button visibility based on scroll position
 */
function updateScrollButtons() {
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        const container = wrapper.parentElement;
        const leftBtn = container.querySelector('.scroll-btn-left');
        const rightBtn = container.querySelector('.scroll-btn-right');

        if (!leftBtn || !rightBtn) return;

        // Show/hide left button
        if (wrapper.scrollLeft <= 10) {
            leftBtn.style.opacity = '0.3';
            leftBtn.style.pointerEvents = 'none';
        } else {
            leftBtn.style.opacity = '1';
            leftBtn.style.pointerEvents = 'auto';
        }

        // Show/hide right button
        const maxScroll = wrapper.scrollWidth - wrapper.clientWidth;
        if (wrapper.scrollLeft >= maxScroll - 10) {
            rightBtn.style.opacity = '0.3';
            rightBtn.style.pointerEvents = 'none';
        } else {
            rightBtn.style.opacity = '1';
            rightBtn.style.pointerEvents = 'auto';
        }
    });
}

// ============================================
// FLASH MESSAGE AUTO-DISMISS
// ============================================

/**
 * Auto-dismiss flash messages after 5 seconds
 */
function setupFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
}

// ============================================
// SMOOTH SCROLL TO TOP
// ============================================

/**
 * Scroll to top of page smoothly
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

/**
 * Handle keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Arrow keys for carousel navigation
        if (e.key === 'ArrowLeft' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            document.querySelectorAll('.carousel-wrapper').forEach(carousel => {
                carousel.scrollBy({ left: -336, behavior: 'smooth' });
            });
        } else if (e.key === 'ArrowRight' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            document.querySelectorAll('.carousel-wrapper').forEach(carousel => {
                carousel.scrollBy({ left: 336, behavior: 'smooth' });
            });
        }

        // Escape key to close modals
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal-overlay');
            if (modal) {
                modal.remove();
            }
        }
    });
}

// ============================================
// CARD HOVER EFFECTS
// ============================================

/**
 * Add enhanced hover effects to cards
 */
function setupCardHoverEffects() {
    document.querySelectorAll('.deck-card, .feature-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            // Add subtle tilt effect
            this.style.transition = 'all 0.3s ease';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// ============================================
// LOADING STATES
// ============================================

/**
 * Show loading spinner on buttons when clicked
 * @param {HTMLElement} button - Button element
 */
function showButtonLoading(button) {
    const originalText = button.innerHTML;
    button.dataset.originalText = originalText;
    button.innerHTML = '<span class="loading-spinner" style="width: 20px; height: 20px; border-width: 2px;"></span>';
    button.disabled = true;
}

/**
 * Hide loading spinner and restore button text
 * @param {HTMLElement} button - Button element
 */
function hideButtonLoading(button) {
    button.innerHTML = button.dataset.originalText || button.innerHTML;
    button.disabled = false;
}

// ============================================
// FORM ENHANCEMENTS
// ============================================

/**
 * Setup form submission with loading states
 */
function setupFormEnhancements() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                showButtonLoading(submitBtn);
            }
        });
    });
}

// ============================================
// MODAL MANAGEMENT
// ============================================

/**
 * Open a modal
 * @param {string} modalId - Modal element ID
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Animate in
        setTimeout(() => {
            modal.style.opacity = '1';
        }, 10);
    }
}

/**
 * Close a modal
 * @param {string} modalId - Modal element ID
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }, 300);
    }
}

/**
 * Setup modal close handlers
 */
function setupModals() {
    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                this.remove();
                document.body.style.overflow = '';
            }
        });
    });

    // Close on close button click
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal-overlay').remove();
            document.body.style.overflow = '';
        });
    });
}

// ============================================
// CSRF TOKEN HELPER
// ============================================

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Add CSRF token to fetch requests
 * @param {object} options - Fetch options
 * @returns {object} Modified options with CSRF token
 */
function addCSRFToken(options = {}) {
    const token = getCSRFToken();
    if (token) {
        options.headers = options.headers || {};
        options.headers['X-CSRFToken'] = token;
    }
    return options;
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Display duration in ms (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} animate-fadeIn`;
    toast.style.position = 'fixed';
    toast.style.top = '100px';
    toast.style.right = '20px';
    toast.style.zIndex = '10001';
    toast.style.maxWidth = '400px';
    toast.innerHTML = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================
// SEARCH FUNCTIONALITY
// ============================================

/**
 * Setup search functionality
 */
function setupSearch() {
    const searchIcon = document.querySelector('.search-icon');
    if (searchIcon) {
        searchIcon.addEventListener('click', function() {
            const searchInput = prompt('Search decks:');
            if (searchInput) {
                window.location.href = `/decks?search=${encodeURIComponent(searchInput)}`;
            }
        });
    }
}

// ============================================
// SCROLL TO TOP BUTTON
// ============================================

/**
 * Show/hide scroll to top button
 */
function setupScrollToTopButton() {
    let scrollBtn = document.getElementById('scrollToTopBtn');

    // Create button if it doesn't exist
    if (!scrollBtn) {
        scrollBtn = document.createElement('button');
        scrollBtn.id = 'scrollToTopBtn';
        scrollBtn.innerHTML = '↑';
        scrollBtn.style.cssText = `
        position: fixed;
        bottom: 40px;
        right: 40px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: var(--gradient-primary);
        color: white;
        border: none;
        font-size: 24px;
        cursor: pointer;
        display: none;
        z-index: 1000;
        box-shadow: var(--shadow-lg);
        transition: var(--transition-base);
        `;
        scrollBtn.onclick = scrollToTop;
        document.body.appendChild(scrollBtn);
    }

    // Show/hide based on scroll position
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'flex';
            scrollBtn.style.alignItems = 'center';
            scrollBtn.style.justifyContent = 'center';
        } else {
            scrollBtn.style.display = 'none';
        }
    });
}

// ============================================
// COPY TO CLIPBOARD
// ============================================

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success', 2000);
    } catch (err) {
        showToast('Failed to copy', 'error', 2000);
    }
}

// ============================================
// CONFIRM DIALOG
// ============================================

/**
 * Show confirmation dialog with custom styling
 * @param {string} message - Message to display
 * @returns {Promise<boolean>} User's choice
 */
function confirmDialog(message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.display = 'flex';

        const modal = document.createElement('div');
        modal.className = 'modal-content';
        modal.style.maxWidth = '400px';

        modal.innerHTML = `
        <div class="modal-header">
        <h3 class="modal-title">Confirm Action</h3>
        </div>
        <div style="padding: 24px 0;">
        <p style="color: var(--color-text-tertiary);">${message}</p>
        </div>
        <div style="display: flex; gap: 12px; justify-content: flex-end;">
        <button class="btn btn-secondary" id="cancelBtn">Cancel</button>
        <button class="btn btn-primary" id="confirmBtn">Confirm</button>
        </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        modal.querySelector('#confirmBtn').onclick = () => {
            overlay.remove();
            document.body.style.overflow = '';
            resolve(true);
        };

        modal.querySelector('#cancelBtn').onclick = () => {
            overlay.remove();
            document.body.style.overflow = '';
            resolve(false);
        };

        overlay.onclick = (e) => {
            if (e.target === overlay) {
                overlay.remove();
                document.body.style.overflow = '';
                resolve(false);
            }
        };
    });
}

// ============================================
// INITIALIZATION
// ============================================

/**
 * Initialize all functionality when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Setup core functionality
    setupFlashMessages();
    setupKeyboardShortcuts();
    setupCardHoverEffects();
    setupFormEnhancements();
    setupModals();
    setupSearch();
    setupScrollToTopButton();

    // Setup carousel scroll tracking
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        wrapper.addEventListener('scroll', updateScrollButtons);
    });

    // Initial scroll button state
    updateScrollButtons();

    // Add smooth reveal animation to cards
    const cards = document.querySelectorAll('.deck-card, .feature-card, .quick-stat-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 50);
    });

    // Add loading class to body when page is ready
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
});

// ============================================
// UTILITY: Debounce Function
// ============================================

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
function debounce(func, wait = 250) {
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

// ============================================
// UTILITY: Throttle Function
// ============================================

/**
 * Throttle function to limit function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in ms
 * @returns {Function} Throttled function
 */
function throttle(func, limit = 250) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for use in other scripts
window.FlashFlow = {
    scrollCarousel,
    updateScrollButtons,
    showToast,
    openModal,
    closeModal,
    copyToClipboard,
    confirmDialog,
    showButtonLoading,
    hideButtonLoading,
    getCSRFToken,
    addCSRFToken,
    debounce,
    throttle
};
