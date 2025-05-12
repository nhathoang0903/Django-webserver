import os
import json

class Translator:
    _instance = None
    _current_language = "vi"
    _translations = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance._load_translations()
        return cls._instance
    
    def _load_translations(self):
        """Load all available translation files"""
        languages_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'languages')
        if not os.path.exists(languages_dir):
            print(f"Warning: Languages directory not found at {languages_dir}")
            return
            
        # Load all JSON files from the languages directory
        for filename in os.listdir(languages_dir):
            if filename.endswith('.json'):
                language_code = filename.split('.')[0]
                file_path = os.path.join(languages_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._translations[language_code] = json.load(f)
                        print(f"Loaded language: {language_code}")
                except Exception as e:
                    print(f"Error loading language file {filename}: {e}")
    
    def get_text(self, key_path, default=None):
        """
        Get translated text using dot notation
        Example: get_text('welcomePage.welcome')
        """
        if not key_path:
            return default if default is not None else key_path
            
        # Navigate through nested dictionary using the key path
        parts = key_path.split('.')
        current = self._translations.get(self._current_language, {})
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Fall back to English if translation not found
                if self._current_language != "en":
                    en_current = self._translations.get("en", {})
                    for en_part in parts:
                        if isinstance(en_current, dict) and en_part in en_current:
                            en_current = en_current[en_part]
                        else:
                            return default if default is not None else key_path
                    return en_current
                return default if default is not None else key_path
        
        return current
    
    def set_language(self, language_code):
        """Set the current language"""
        if language_code in self._translations:
            self._current_language = language_code
            print(f"Language set to: {language_code}")
            return True
        else:
            print(f"Language {language_code} not available, using default")
            return False
    
    def get_current_language(self):
        """Get the current language code"""
        return self._current_language
    
    def get_available_languages(self):
        """Get a list of available language codes"""
        return list(self._translations.keys())
    
    def language_is_loaded(self, language_code):
        """Check if a language is loaded"""
        return language_code in self._translations

# Helper function for easy access
def _(key_path, default=None):
    """
    Get translated text for the given key path
    Example: _('welcomePage.welcome')
    """
    translator = Translator()
    return translator.get_text(key_path, default)

# Helper function to set language
def set_language(language_code):
    """Set the current language"""
    translator = Translator()
    return translator.set_language(language_code)

# Helper function to get current language
def get_current_language():
    """Get the current language code"""
    translator = Translator()
    return translator.get_current_language() 