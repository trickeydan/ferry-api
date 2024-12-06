const THEME_ICON_MAP = {light: 'bi-sun-fill', dark: 'bi-moon-stars-fill', auto: 'bi-circle-half'};

class ThemeSwitcher {

    constructor() {
        this.setTheme(this.getPreferredTheme())
    }

    getStoredTheme = () => localStorage.getItem('theme')
    setStoredTheme = theme => localStorage.setItem('theme', theme)

    getPreferredTheme() {
        const storedTheme = this.getStoredTheme();
        if (storedTheme) {
            return storedTheme
        }
    
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }

    setTheme(theme) {
        if (theme === 'auto') {
            document.documentElement.setAttribute('data-bs-theme', (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
        } else {
            document.documentElement.setAttribute('data-bs-theme', theme)
        }
    }

    showActiveTheme(theme, focus = false) {
        const themeSwitcher = document.querySelector('#ferry-theme')
    
        if (!themeSwitcher) {
            return
        }
    
        const themeSwitcherText = document.querySelector('#ferry-theme-text')
        const activeThemeIcon = document.getElementById('ferry-theme-active-icon')
        const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`)
    
        document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
            element.classList.remove('active')
            element.setAttribute('aria-pressed', 'false')
        })
    
        btnToActive.classList.add('active')
        btnToActive.setAttribute('aria-pressed', 'true')

        activeThemeIcon.classList.remove(...Object.values(THEME_ICON_MAP));
        activeThemeIcon.classList.add(THEME_ICON_MAP[theme])

        const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`
        themeSwitcher.setAttribute('aria-label', themeSwitcherLabel)
    
        if (focus) {
            themeSwitcher.focus()
        }
    }
}

const themeSwitcher = new ThemeSwitcher();

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const storedTheme = themeSwitcher.getStoredTheme()
    if (storedTheme !== 'light' && storedTheme !== 'dark') {
        setTheme(getPreferredTheme())
    }
})

window.addEventListener('DOMContentLoaded', () => {
    themeSwitcher.showActiveTheme(themeSwitcher.getPreferredTheme())

    document.querySelectorAll('[data-bs-theme-value]')
    .forEach(toggle => {
        toggle.addEventListener('click', () => {
            const theme = toggle.getAttribute('data-bs-theme-value')
            themeSwitcher.setStoredTheme(theme)
            themeSwitcher.setTheme(theme)
            themeSwitcher.showActiveTheme(theme, true)
        })
    })
})