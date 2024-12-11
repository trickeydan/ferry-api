const THEME_ICON_MAP = {
  light: "bi-sun-fill",
  dark: "bi-moon-stars-fill",
  auto: "bi-circle-half",
} as const;

type ThemeKey = keyof typeof THEME_ICON_MAP;

class ThemeSwitcher {

    constructor() {
        this.setTheme(this.getPreferredTheme())
    }

    getStoredTheme(): ThemeKey {
      return localStorage.getItem('theme') as ThemeKey;
    }

    setStoredTheme(theme: ThemeKey) {
      localStorage.setItem('theme', theme)
    } 

    getPreferredTheme(): ThemeKey {
        const storedTheme = this.getStoredTheme();
        if (storedTheme) {
            return storedTheme
        }
    
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }

    setTheme(theme: ThemeKey) {
        if (theme === 'auto') {
            document.documentElement.setAttribute('data-bs-theme', (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
        } else {
            document.documentElement.setAttribute('data-bs-theme', theme)
        }
    }

    showActiveTheme(theme: ThemeKey, focus = false) {
        const themeSwitcher: HTMLButtonElement | null = document.querySelector('#ferry-theme')
    
        if (!themeSwitcher) {
            return
        }
    
        const themeSwitcherText: HTMLElement = document.querySelector('#ferry-theme-text')!
        const activeThemeIcon: HTMLElement = document.getElementById('ferry-theme-active-icon')!
        const btnToActive = document.querySelector<HTMLElement>(`[data-bs-theme-value="${theme}"]`)!
    
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

function initialiseThemeSwitcher(){
    const themeSwitcher = new ThemeSwitcher();

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const storedTheme = themeSwitcher.getStoredTheme()
        if (storedTheme !== 'light' && storedTheme !== 'dark') {
            themeSwitcher.setTheme(themeSwitcher.getPreferredTheme())
        }
    })

    window.addEventListener('DOMContentLoaded', () => {
        themeSwitcher.showActiveTheme(themeSwitcher.getPreferredTheme())

        document.querySelectorAll('[data-bs-theme-value]')
        .forEach(toggle => {
            toggle.addEventListener('click', () => {
                const theme = toggle.getAttribute('data-bs-theme-value')! as ThemeKey
                themeSwitcher.setStoredTheme(theme)
                themeSwitcher.setTheme(theme)
                themeSwitcher.showActiveTheme(theme, true)
            })
        })
    })
}

export {initialiseThemeSwitcher};