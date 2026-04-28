// Модальные окна
let avatarModal, editProfileModal, passwordModal;
let cropper = null;
let croppedAvatarData = null;

// Система уведомлений
function showToast(message, type = 'info', title = '', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${type}`;
    
    // Иконка по типу
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
    
    // Автоматическое удаление
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Подтверждение действий (замена confirm)
function showConfirm(message, onConfirm, title = 'Подтверждение') {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.2s ease;
    `;
    
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        background: #1e1e1e;
        border-radius: 16px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        animation: scaleIn 0.2s ease;
    `;
    
    dialog.innerHTML = `
        <h5 style="margin-bottom: 16px; display: flex; align-items: center; gap: 10px;">
            <i class="fas fa-question-circle" style="color: #2196f3; font-size: 24px;"></i>
            ${title}
        </h5>
        <p style="margin-bottom: 24px; opacity: 0.9;">${message}</p>
        <div style="display: flex; gap: 12px; justify-content: flex-end;">
            <button class="btn btn-secondary" id="confirm-cancel">Отмена</button>
            <button class="btn btn-danger" id="confirm-ok">Подтвердить</button>
        </div>
    `;
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // Добавляем стили анимации если их нет
    if (!document.getElementById('confirm-animations')) {
        const style = document.createElement('style');
        style.id = 'confirm-animations';
        style.textContent = `
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes scaleIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        `;
        document.head.appendChild(style);
    }
    
    dialog.querySelector('#confirm-cancel').onclick = () => overlay.remove();
    dialog.querySelector('#confirm-ok').onclick = () => {
        overlay.remove();
        onConfirm();
    };
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
}

document.addEventListener('DOMContentLoaded', function() {
    avatarModal = new bootstrap.Modal(document.getElementById('avatarEditorModal'));
    editProfileModal = new bootstrap.Modal(document.getElementById('editProfileModal'));
    passwordModal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
    
    initAvatarEditor();
});

function initAvatarEditor() {
    const fileInput = document.getElementById('avatar-file-input');
    const editorCard = document.getElementById('avatar-editor-card');
    const editorImage = document.getElementById('avatar-editor-image');
    
    if (!fileInput) return;
    
    // Сохраняем оригинальный аватар при открытии модального окна
    let originalAvatarSrc = document.getElementById('main-avatar').src;
    
    fileInput.removeEventListener('change', handleFileSelect);
    fileInput.addEventListener('change', handleFileSelect);
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        if (file.size > 5 * 1024 * 1024) {
            showToast('Файл слишком большой. Максимальный размер 5MB', 'error');
            fileInput.value = '';
            return;
        }
        
        if (!file.type.match('image.*')) {
            showToast('Пожалуйста, выберите изображение', 'error');
            fileInput.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            editorCard.style.display = 'block';
            editorImage.src = e.target.result;
            
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }
            
            cropper = new Cropper(editorImage, {
                aspectRatio: 1,
                viewMode: 2,
                dragMode: 'move',
                autoCropArea: 1,
                restore: false,
                guides: true,
                center: true,
                highlight: true,
                cropBoxMovable: true,
                cropBoxResizable: true,
                background: false,
                rotatable: true,
                scalable: true,
                zoomable: true
            });
        };
        reader.readAsDataURL(file);
    }
    
    function safeCropperAction(action) {
        if (cropper) action();
    }
    
    document.getElementById('avatar-rotate-left')?.addEventListener('click', () => safeCropperAction(() => cropper.rotate(-90)));
    document.getElementById('avatar-rotate-right')?.addEventListener('click', () => safeCropperAction(() => cropper.rotate(90)));
    document.getElementById('avatar-flip-h')?.addEventListener('click', () => safeCropperAction(() => {
        const scaleX = cropper.getData().scaleX || 1;
        cropper.scaleX(-scaleX);
    }));
    document.getElementById('avatar-flip-v')?.addEventListener('click', () => safeCropperAction(() => {
        const scaleY = cropper.getData().scaleY || 1;
        cropper.scaleY(-scaleY);
    }));
    document.getElementById('avatar-zoom-in')?.addEventListener('click', () => safeCropperAction(() => cropper.zoom(0.1)));
    document.getElementById('avatar-zoom-out')?.addEventListener('click', () => safeCropperAction(() => cropper.zoom(-0.1)));
    document.getElementById('avatar-reset')?.addEventListener('click', () => safeCropperAction(() => cropper.reset()));
    
	document.getElementById('avatar-apply-crop')?.addEventListener('click', function() {
		if (!cropper) {
			showToast('Сначала выберите изображение', 'warning');
			return;
		}
		
		const canvas = cropper.getCroppedCanvas({
			width: 300,
			height: 300,
			imageSmoothingEnabled: true,
			imageSmoothingQuality: 'high'
		});
		
		if (canvas) {
			croppedAvatarData = canvas.toDataURL('image/jpeg', 0.9);
			document.getElementById('avatar-result-section').style.display = 'block';
			
			// Обновляем аватар на странице
			document.getElementById('main-avatar').src = croppedAvatarData;
			document.getElementById('current-avatar-preview').src = croppedAvatarData;
			
			showToast('Изображение обработано! Нажмите "Сохранить фото"', 'success');
		}
	});
    
    // При открытии модального окна сохраняем текущий аватар
    document.getElementById('avatarEditorModal')?.addEventListener('shown.bs.modal', function() {
        originalAvatarSrc = document.getElementById('main-avatar').src;
        console.log('Modal opened, saved avatar:', originalAvatarSrc);
    });
    
    // При закрытии модального окна (Отмена, крестик, клик вне окна)
    document.getElementById('avatarEditorModal')?.addEventListener('hidden.bs.modal', function() {
        // Уничтожаем cropper
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        
        // Скрываем редактор и результат
        editorCard.style.display = 'none';
        document.getElementById('avatar-result-section').style.display = 'none';
        
        // Очищаем input
        fileInput.value = '';
        
        // Если не было сохранения (нет croppedAvatarData или окно закрыто без сохранения)
        // Восстанавливаем оригинальный аватар
        if (!croppedAvatarData) {
            document.getElementById('main-avatar').src = originalAvatarSrc;
            document.getElementById('current-avatar-preview').src = originalAvatarSrc;
            console.log('Modal closed without save, restored:', originalAvatarSrc);
        }
        
        // Сбрасываем данные кадрирования
        croppedAvatarData = null;
    });
}

// Исправленная функция открытия редактора
function openAvatarEditor() {
    // Сбрасываем все состояния
    croppedAvatarData = null;
    document.getElementById('avatar-editor-card').style.display = 'none';
    document.getElementById('avatar-result-section').style.display = 'none';
    document.getElementById('avatar-file-input').value = '';
    
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    
    // Убеждаемся, что превью показывает текущий аватар
    const currentAvatar = document.getElementById('main-avatar').src;
    document.getElementById('current-avatar-preview').src = currentAvatar;
    
    avatarModal.show();
}

// функция сохранения аватара
async function saveAvatarOnly() {
    if (!croppedAvatarData) {
        showToast('Сначала обработайте изображение', 'warning');
        return;
    }
    
    // Получаем текущие данные из DOM
    const userName = document.querySelector('h3.mb-1')?.textContent?.trim() || '';
    const nameParts = userName.split(' ');
    const currentSurname = nameParts[0] || '';
    const currentName = nameParts[1] || '';
    
    // Получаем телефон из DOM
    const phoneElement = document.querySelector('.fa-phone')?.parentElement;
    const currentPhone = phoneElement?.textContent?.trim() || '';
    
    // Получаем остальные данные из скрытых полей или из атрибутов
    const currentThname = document.getElementById('edit-thname')?.value || '';
    const currentBirthday = document.getElementById('edit-birthday')?.value || '';
    
    const formData = new FormData();
    formData.append('cropped_image', croppedAvatarData);
    formData.append('name', currentName);
    formData.append('surname', currentSurname);
    formData.append('thname', currentThname);
    formData.append('birthday', currentBirthday);
    formData.append('tnumber', currentPhone);
    
    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Фото профиля обновлено!', 'success');
            avatarModal.hide();
            croppedAvatarData = null;
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.error || 'Ошибка при сохранении', 'error');
        }
    } catch (error) {
        showToast('Ошибка при сохранении: ' + error, 'error');
    }
}

function openEditProfile() {
    editProfileModal.show();
}

async function saveProfileData() {
    const form = document.getElementById('profileForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Профиль обновлен!', 'success');
            editProfileModal.hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.error || 'Ошибка при сохранении', 'error');
        }
    } catch (error) {
        showToast('Ошибка: ' + error, 'error');
    }
}

function openChangePassword() {
    passwordModal.show();
}

async function changePassword() {
    const current = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirm = document.getElementById('confirm-password').value;
    
    if (!current || !newPass || !confirm) {
        showToast('Все поля обязательны для заполнения', 'warning');
        return;
    }
    
    if (newPass !== confirm) {
        showToast('Пароли не совпадают', 'error');
        return;
    }
    
    if (newPass.length < 8) {
        showToast('Пароль должен быть не менее 8 символов', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/profile/change-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                current_password: current,
                new_password: newPass
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Пароль успешно изменен!', 'success');
            passwordModal.hide();
            document.getElementById('passwordForm').reset();
        } else {
            showToast(data.error || 'Ошибка при смене пароля', 'error');
        }
    } catch (error) {
        showToast('Ошибка: ' + error, 'error');
    }
}

function deleteMyReview(reviewId) {
    showConfirm('Вы уверены, что хотите удалить этот отзыв?', async () => {
        try {
            const response = await fetch(`/delete_review/${reviewId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Отзыв удален', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showToast(data.error || 'Ошибка при удалении', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error, 'error');
        }
    }, 'Удаление отзыва');
}

// Глобальные функции
window.openAvatarEditor = openAvatarEditor;
window.saveAvatarOnly = saveAvatarOnly;
window.openEditProfile = openEditProfile;
window.saveProfileData = saveProfileData;
window.openChangePassword = openChangePassword;
window.changePassword = changePassword;
window.deleteMyReview = deleteMyReview;