import os
import time
from gtts import gTTS
from googletrans import LANGUAGES, Translator

translator = Translator()  # Initialize the translator module.

# Create a mapping between language names and language codes
language_mapping = {name: code for code, name in LANGUAGES.items()}

def get_language_code(language_name):
    return language_mapping.get(language_name, language_name)

def translator_function(spoken_text, from_language, to_language):
    return translator.translate(spoken_text, src='{}'.format(from_language), dest='{}'.format(to_language))

def main():
    print("=" * 50)
    print("Real-Time Language Translator Demo")
    print("=" * 50)
    
    # Example translation
    test_text = "Hello, how are you?"
    
    print("\nAvailable Languages (first 10):")
    languages = list(LANGUAGES.values())
    for i, lang in enumerate(languages[:10]):
        print(f"  {i+1}. {lang}")
    
    # Translate English to Spanish
    from_lang = "en"  # English
    to_lang = "es"    # Spanish
    
    print(f"\n--- Translation Test ---")
    print(f"Input Text: {test_text}")
    print(f"Source Language: {LANGUAGES.get(from_lang, 'Unknown')}")
    print(f"Target Language: {LANGUAGES.get(to_lang, 'Unknown')}")
    
    try:
        print("\nTranslating...")
        result = translator_function(test_text, from_lang, to_lang)
        print(f"Translated Text: {result.text}")
        print("\n✓ Translation successful!")
        
    except Exception as e:
        print(f"✗ Error during translation: {e}")
    
    # Test with more examples
    print("\n" + "=" * 50)
    print("Additional Translation Examples:")
    print("=" * 50)
    
    test_cases = [
        ("Hello", "en", "fr"),      # English to French
        ("Hello", "en", "de"),      # English to German
        ("Hello", "en", "ja"),      # English to Japanese
        ("Good morning", "en", "es"), # English to Spanish
    ]
    
    for text, src, tgt in test_cases:
        try:
            result = translator_function(text, src, tgt)
            src_name = LANGUAGES.get(src, 'Unknown')
            tgt_name = LANGUAGES.get(tgt, 'Unknown')
            print(f"\n{src_name}: {text}")
            print(f"{tgt_name}: {result.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
