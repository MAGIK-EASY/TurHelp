// ========== Система уведомлений (Toast) ==========
function showToast(message, type = 'info', title = '', duration = 4000) {
    let container = document.getElementById('toast-container');
    
    // Создаем контейнер если его нет
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${type}`;
    
    let icon = '';
    let defaultTitle = '';
    switch(type) {
        case 'success':
            icon = '<i class="fas fa-check-circle"></i>';
            defaultTitle = 'Успешно';
            break;
        case 'error':
            icon = '<i class="fas fa-times-circle"></i>';
            defaultTitle = 'Ошибка';
            break;
        case 'warning':
            icon = '<i class="fas fa-exclamation-triangle"></i>';
            defaultTitle = 'Внимание';
            break;
        default:
            icon = '<i class="fas fa-info-circle"></i>';
            defaultTitle = 'Информация';
    }
    
    const finalTitle = title || defaultTitle;
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            <div class="toast-title">${finalTitle}</div>
            <div class="toast-message">${message}</div>
        </div>
        <div class="toast-close" onclick="this.closest('.custom-toast').remove()">
            <i class="fas fa-times"></i>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ========== Вспомогательные функции ==========
function showMessage(containerId, text, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show py-2" role="alert">
            <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            ${text}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

function clearMessages(containerId) {
    const container = document.getElementById(containerId);
    if (container) container.innerHTML = '';
}

function checkPasswordMatch() {
    const password = document.getElementById('reg-password')?.value;
    const confirm = document.getElementById('reg-confirm')?.value;
    const message = document.getElementById('reg-password-message');
    
    if (!message) return;
    
    if (password && confirm) {
        if (password === confirm) {
            message.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Пароли совпадают</span>';
        } else {
            message.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle"></i> Пароли не совпадают</span>';
        }
    } else {
        message.innerHTML = '';
    }
}

// ========== Модальные окна ==========
let loginModal, registerModal;

document.addEventListener('DOMContentLoaded', function() {
    const loginModalEl = document.getElementById('loginModal');
    const registerModalEl = document.getElementById('registerModal');
    
    if (loginModalEl) loginModal = new bootstrap.Modal(loginModalEl);
    if (registerModalEl) registerModal = new bootstrap.Modal(registerModalEl);
    
    // Обработчик входа
    document.getElementById('modal-login-form')?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        if (document.getElementById('modal-remember')?.checked) {
            formData.append('remember-me', 'on');
        }
        
        clearMessages('login-messages');
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Вход...';
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Вход выполнен успешно!', 'success');
                loginModal.hide();
                setTimeout(() => window.location.reload(), 500);
            } else {
                showMessage('login-messages', data.error || 'Ошибка входа', 'danger');
                showToast(data.error || 'Ошибка входа', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('login-messages', 'Ошибка соединения с сервером', 'danger');
            showToast('Ошибка соединения', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
    
    // Обработчик регистрации
    document.getElementById('modal-register-form')?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const password = document.getElementById('reg-password')?.value;
        const confirm = document.getElementById('reg-confirm')?.value;
        
        if (password !== confirm) {
            showMessage('register-messages', 'Пароли не совпадают', 'danger');
            showToast('Пароли не совпадают', 'error');
            return;
        }
        
        if (password.length < 8) {
            showMessage('register-messages', 'Пароль должен быть не менее 8 символов', 'danger');
            showToast('Пароль должен быть не менее 8 символов', 'error');
            return;
        }
        
        const formData = new FormData(this);
        clearMessages('register-messages');
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Регистрация...';
        
        try {
            const response = await fetch('/registrations', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Регистрация успешна! Добро пожаловать!', 'success');
                registerModal.hide();
                setTimeout(() => window.location.reload(), 500);
            } else {
                showMessage('register-messages', data.error || 'Ошибка регистрации', 'danger');
                showToast(data.error || 'Ошибка регистрации', 'error');
            }
        } catch (error) {
            console.error('Register error:', error);
            showMessage('register-messages', 'Ошибка соединения с сервером', 'danger');
            showToast('Ошибка соединения', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
});

// ========== Функции переключения модалок ==========
function switchToRegister() {
    if (loginModal) loginModal.hide();
    if (registerModal) {
        clearMessages('register-messages');
        document.getElementById('modal-register-form')?.reset();
        document.getElementById('reg-password-message').innerHTML = '';
        registerModal.show();
    }
}

function switchToLogin() {
    if (registerModal) registerModal.hide();
    if (loginModal) {
        clearMessages('login-messages');
        document.getElementById('modal-login-form')?.reset();
        loginModal.show();
    }
}

function openLoginModal() {
    if (loginModal) {
        clearMessages('login-messages');
        document.getElementById('modal-login-form')?.reset();
        loginModal.show();
    } else {
        window.location.href = '/login';
    }
}

function openRegisterModal() {
    if (registerModal) {
        clearMessages('register-messages');
        document.getElementById('modal-register-form')?.reset();
        document.getElementById('reg-password-message').innerHTML = '';
        registerModal.show();
    } else {
        window.location.href = '/registrations';
    }
}

// Делаем функции глобально доступными
window.showToast = showToast;
window.showMessage = showMessage;
window.clearMessages = clearMessages;
window.checkPasswordMatch = checkPasswordMatch;
window.switchToRegister = switchToRegister;
window.switchToLogin = switchToLogin;
window.openLoginModal = openLoginModal;
window.openRegisterModal = openRegisterModal;