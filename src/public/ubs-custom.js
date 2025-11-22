// UBS Enhanced Custom JavaScript - Logo Management + Send Icon + Animations
(function() {
    'use strict';

    // Wait for page to load
    window.addEventListener('load', function() {
        console.log('UBS Enhanced custom JS loaded');
        
        // UBS Logo Management
        function manageUBSLogo() {
            // Force UBS logo in header
            const header = document.querySelector('.cl-header, [class*="header"], header');
            if (header) {
                // Remove any existing logos
                const existingLogos = header.querySelectorAll('img, .cl-logo, [class*="logo"], svg');
                existingLogos.forEach(logo => {
                    if (!logo.src.includes('ubs_logo')) {
                        logo.style.display = 'none';
                    }
                });
                
                // Create or update UBS logo
                let ubsLogo = header.querySelector('img[src*="ubs_logo"], .ubs-logo');
                if (!ubsLogo) {
                    ubsLogo = document.createElement('img');
                    ubsLogo.src = '/public/ubs_logo.png';
                    ubsLogo.className = 'ubs-logo';
                    ubsLogo.alt = 'UBS Logo';
                    ubsLogo.style.cssText = `
                        display: block !important;
                        max-height: 40px !important;
                        width: auto !important;
                        margin: 0 auto 16px !important;
                        max-width: 120px !important;
                    `;
                    header.insertBefore(ubsLogo, header.firstChild);
                }
            }
            
            // Force logo in any avatar or branding area
            const avatars = document.querySelectorAll('.cl-avatar, [class*="avatar"], .cl-author');
            avatars.forEach(avatar => {
                const img = avatar.querySelector('img');
                if (img && !img.src.includes('ubs_logo')) {
                    img.src = '/public/ubs_logo.png';
                    img.alt = 'UBS';
                }
            });
        }
        
        // Enhanced Send Icon Management - UBS Red
        function forceSendIconRed() {
            const allButtons = document.querySelectorAll('button, [role="button"]');
            
            allButtons.forEach(button => {
                const ariaLabel = button.getAttribute('aria-label') || '';
                const title = button.getAttribute('title') || '';
                const type = button.getAttribute('type') || '';
                const className = button.className.toLowerCase();
                
                // Skip non-send buttons (copy, theme, logo, etc.)
                if (
                    ariaLabel.toLowerCase().includes('copy') ||
                    title.toLowerCase().includes('copy') ||
                    ariaLabel.toLowerCase().includes('theme') ||
                    title.toLowerCase().includes('theme') ||
                    ariaLabel.toLowerCase().includes('logo') ||
                    title.toLowerCase().includes('logo') ||
                    className.includes('theme') ||
                    className.includes('copy') ||
                    button.closest('header') && !button.closest('.cl-input-container')
                ) {
                    return;
                }
                
                // Target send/submit buttons specifically
                const isSendButton = 
                    type === 'submit' ||
                    ariaLabel.toLowerCase().includes('send') ||
                    ariaLabel.toLowerCase().includes('submit') ||
                    title.toLowerCase().includes('send') ||
                    title.toLowerCase().includes('submit') ||
                    className.includes('send') ||
                    className.includes('submit') ||
                    button.closest('.cl-input-container') ||
                    button.closest('[class*="input"]') ||
                    button.closest('form');
                
                if (isSendButton) {
                    // Clean button styling
                    button.style.cssText += `
                        background: transparent !important;
                        border: none !important;
                        color: #E60000 !important;
                        padding: 8px !important;
                        border-radius: 50% !important;
                        transition: all 0.2s ease !important;
                        width: 40px !important;
                        height: 40px !important;
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                    `;
                    
                    // Force UBS red on all icons within the button
                    const icons = button.querySelectorAll('svg, svg *, path, circle, rect, polygon, line');
                    icons.forEach(icon => {
                        icon.style.cssText += `
                            color: #E60000 !important;
                            fill: #E60000 !important;
                            stroke: #E60000 !important;
                            stroke-width: 2px !important;
                        `;
                    });
                    
                    // Add hover animation
                    button.addEventListener('mouseenter', () => {
                        button.style.background = 'rgba(230, 0, 0, 0.1)';
                        button.style.transform = 'scale(1.05)';
                    });
                    
                    button.addEventListener('mouseleave', () => {
                        button.style.background = 'transparent';
                        button.style.transform = 'scale(1)';
                    });
                }
            });
        }
        
        // Add professional animations
        function addProfessionalAnimations() {
            // Smooth entrance for messages
            const messages = document.querySelectorAll('.cl-message');
            messages.forEach((msg, index) => {
                msg.style.opacity = '0';
                msg.style.transform = 'translateY(10px)';
                setTimeout(() => {
                    msg.style.transition = 'all 0.3s ease';
                    msg.style.opacity = '1';
                    msg.style.transform = 'translateY(0)';
                }, index * 100);
            });
            
            // Input focus animation
            const inputs = document.querySelectorAll('.cl-input, input[type="text"], textarea');
            inputs.forEach(input => {
                input.addEventListener('focus', () => {
                    input.parentElement.style.transform = 'scale(1.02)';
                });
                
                input.addEventListener('blur', () => {
                    input.parentElement.style.transform = 'scale(1)';
                });
            });
        }
        
        // New Chat Confirmation
        function addNewChatConfirmation() {
            const buttons = document.querySelectorAll('button, a, [role="button"]');
            
            buttons.forEach(button => {
                const ariaLabel = button.getAttribute('aria-label') || '';
                const title = button.getAttribute('title') || '';
                const text = button.textContent?.trim() || '';
                
                if (
                    ariaLabel.toLowerCase().includes('new') ||
                    title.toLowerCase().includes('new') ||
                    text.toLowerCase().includes('new chat') ||
                    text.toLowerCase().includes('new conversation') ||
                    text.toLowerCase().includes('start new')
                ) {
                    // Add confirmation dialog
                    const originalClick = button.onclick || button.onsubmit;
                    
                    button.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        if (confirm('Are you sure you want to start a new conversation? Your current conversation will be saved.')) {
                            if (originalClick) {
                                originalClick.call(button, e);
                            } else if (button.href) {
                                window.location.href = button.href;
                            } else {
                                // Trigger original behavior
                                setTimeout(() => {
                                    button.click();
                                }, 50);
                            }
                        }
                    }, { once: true });
                }
            });
        }
        
        // Force message alignment and styling - NUCLEAR MODE
        function enforceMessageStyling() {
            // 1. Find the ROOT message rows
            const rows = document.querySelectorAll('.cl-message-user, .cl-message-ai');
            
            rows.forEach(row => {
                // FORCE CONTAINER LAYOUT
                row.style.cssText = `
                    display: flex !important;
                    width: 100% !important;
                    background: transparent !important;
                    box-shadow: none !important;
                    border: none !important;
                `;
                
                // ALIGNMENT
                if (row.classList.contains('cl-message-user')) {
                    row.style.justifyContent = 'flex-end';
                    row.style.paddingRight = '20px';
                } else {
                    row.style.justifyContent = 'flex-start';
                    row.style.paddingLeft = '20px';
                }
                
                // 2. FIND THE BUBBLE (the element with the text)
                // We look for the deepest div that has text content
                const bubble = row.querySelector('.cl-message-content');
                
                if (bubble) {
                    bubble.style.cssText = `
                        background-color: #FFFFFF !important;
                        border: 1px solid #E8E8E8 !important;
                        border-left: 4px solid #003087 !important;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04) !important;
                        padding: 20px 24px !important;
                        border-radius: 0 !important;
                        color: #333333 !important;
                        max-width: 650px !important;
                        min-width: 100px !important;
                        transition: all 0.2s ease !important;
                    `;
                    
                    // Add hover effect manually via JS since inline styles override CSS hover
                    bubble.onmouseenter = function() {
                        this.style.transform = 'translateY(-1px)';
                        this.style.boxShadow = '0 6px 16px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06)';
                        this.style.borderLeftColor = '#E60000';
                    };
                    
                    bubble.onmouseleave = function() {
                        this.style.transform = 'translateY(0)';
                        this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)';
                        this.style.borderLeftColor = '#003087';
                    };
                }
                
                // 3. KILL EVERYTHING ELSE (Nested shadows, backgrounds)
                const others = row.querySelectorAll('*');
                others.forEach(el => {
                    if (el !== bubble && !bubble.contains(el)) {
                        el.style.background = 'transparent';
                        el.style.boxShadow = 'none';
                        el.style.border = 'none';
                    }
                });
            });
        }

        // Initialize everything
        function initializeUBSTheme() {
            manageUBSLogo();
            forceSendIconRed();
            addProfessionalAnimations();
            addNewChatConfirmation();
            enforceMessageStyling();
        }
        
        // Run immediately
        initializeUBSTheme();
        
        // Watch for DOM changes (dynamic content)
        const observer = new MutationObserver(function(mutations) {
            let shouldUpdate = false;
            mutations.forEach(mutation => {
                if (mutation.type === 'childList' && 
                    (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0)) {
                    shouldUpdate = true;
                }
            });
            
            if (shouldUpdate) {
                // Debounce updates
                clearTimeout(window.ubsUpdateTimer);
                window.ubsUpdateTimer = setTimeout(initializeUBSTheme, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'src']
        });
        
        // Periodic cleanup for dynamic elements
        setInterval(() => {
            forceSendIconRed();
            manageUBSLogo();
            enforceMessageStyling();
        }, 500);
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                setTimeout(initializeUBSTheme, 200);
            }
        });
    });
    
    // Fallback for immediate execution if DOM is already loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                console.log('UBS fallback initialization');
                // Quick logo and send button fix
                const header = document.querySelector('.cl-header, header');
                if (header) {
                    const logo = document.createElement('img');
                    logo.src = '/public/ubs_logo.png';
                    logo.style.cssText = 'display: block; max-height: 40px; margin: 0 auto 16px;';
                    header.appendChild(logo);
                }
            }, 500);
        });
    }
})();
