// theme.js
document.addEventListener('DOMContentLoaded', function() {
    const themeBtn = document.getElementById('theme-switcher-btn');
    const html = document.documentElement;
    
    // Проверяем сохранённую тему
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        html.setAttribute('data-bs-theme', savedTheme);
        updateThemeIcon(savedTheme);
    }
    
    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            html.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        if (themeBtn) {
            const icon = themeBtn.querySelector('i');
            if (theme === 'light') {
                icon.className = 'fas fa-sun';
            } else {
                icon.className = 'fas fa-moon';
            }
        }
    }
});