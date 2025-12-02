"""
Real-Time Language Translator Backend API
Provides REST endpoints for text translation, speech recognition, and text-to-speech synthesis
"""

import os
import io
import tempfile
import logging
import time
from datetime import datetime
from functools import lru_cache

from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
from googletrans import Translator, LANGUAGES
from gtts import gTTS

# Import configuration
try:
    from config import (
        DEBUG, HOST, PORT, FLASK_ENV, CORS_ORIGINS,
        MAX_TEXT_LENGTH, REQUEST_TIMEOUT, ENABLE_SPEECH_RECOGNITION,
        ENABLE_TEXT_TO_SPEECH, LOG_LEVEL, LOG_FILE
    )
except ImportError:
    # Fallback defaults if config not found
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    FLASK_ENV = 'development'
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
    MAX_TEXT_LENGTH = 5000
    REQUEST_TIMEOUT = 30
    ENABLE_SPEECH_RECOGNITION = True
    ENABLE_TEXT_TO_SPEECH = True
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'translator.log'

# Import database modules
try:
    from database import db, translation_repo
    DATABASE_AVAILABLE = False
except ImportError as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Database module not available: {e}")
    db = None
    translation_repo = None
    DATABASE_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize translator (global instance)
translator = Translator()

def get_translator():
    """Get a translator instance - creates fresh one to avoid rate limiting"""
    return Translator()

# Initialize database connection
if db is not None:
    try:
        if db.create_database_if_not_exists():
            if db.connect():
                db.create_tables()
                DATABASE_AVAILABLE = True
                logger.info("Database connected and initialized successfully")
            else:
                logger.warning("⚠ Could not connect to database - running in memory mode")
                DATABASE_AVAILABLE = False
        else:
            logger.warning("⚠ Could not create database - running in memory mode")
            DATABASE_AVAILABLE = False
    except Exception as e:
        logger.warning(f"⚠ Database initialization failed: {e} - running in memory mode")
        DATABASE_AVAILABLE = False
else:
    logger.warning("⚠ Database module not available - running in memory mode")
    DATABASE_AVAILABLE = False

# Cache language mappings
@lru_cache(maxsize=1)
def get_language_mapping():
    """Get cached language code to name mapping"""
    return {code: name for code, name in LANGUAGES.items()}

@lru_cache(maxsize=1)
def get_reverse_language_mapping():
    """Get cached language name to code mapping"""
    return {name: code for code, name in LANGUAGES.items()}

def validate_language_code(lang_code):
    """Validate if language code exists"""
    return lang_code in LANGUAGES

def get_language_code(language_name):
    """Convert language name to code"""
    mapping = get_reverse_language_mapping()
    return mapping.get(language_name, language_name)

# ============ API Endpoints ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/api/languages', methods=['GET'])
def get_languages():
    """Get list of supported languages"""
    try:
        languages = get_language_mapping()
        language_list = [
            {'code': code, 'name': name}
            for code, name in sorted(languages.items(), key=lambda x: x[1])
        ]
        return jsonify({
            'success': True,
            'languages': language_list,
            'count': len(language_list)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching languages: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch languages'
        }), 500

@app.route('/api/translate', methods=['POST'])
def translate():
    """
    Translate text from one language to another
    
    Request body:
    {
        "text": "text to translate",
        "source_lang": "en",
        "target_lang": "es",
        "source_lang_name": "English" (optional, alternative to source_lang)
        "target_lang_name": "Spanish" (optional, alternative to target_lang)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Extract text
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'Text field is required'}), 400
        
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                'success': False,
                'error': f'Text exceeds maximum length of {MAX_TEXT_LENGTH} characters'
            }), 400
        
        # Get source language
        source_lang = data.get('source_lang')
        if not source_lang:
            source_lang_name = data.get('source_lang_name')
            if source_lang_name:
                source_lang = get_language_code(source_lang_name)
            else:
                return jsonify({'success': False, 'error': 'source_lang or source_lang_name is required'}), 400
        
        # Get target language
        target_lang = data.get('target_lang')
        if not target_lang:
            target_lang_name = data.get('target_lang_name')
            if target_lang_name:
                target_lang = get_language_code(target_lang_name)
            else:
                return jsonify({'success': False, 'error': 'target_lang or target_lang_name is required'}), 400
        
        # Validate language codes
        if not validate_language_code(source_lang):
            return jsonify({'success': False, 'error': f'Invalid source language: {source_lang}'}), 400
        
        if not validate_language_code(target_lang):
            return jsonify({'success': False, 'error': f'Invalid target language: {target_lang}'}), 400
        
        # Perform translation with retry logic
        start_time = time.time()
        logger.info(f"Translating from {source_lang} to {target_lang}: {text[:50]}...")
        
        result = None
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Get fresh translator instance for each request
                trans = get_translator()
                result = trans.translate(text, src=source_lang, dest=target_lang)
                
                # Validate result before breaking
                if result and hasattr(result, 'text') and result.text and result.text.strip():
                    logger.info(f"Translation successful on attempt {attempt + 1}")
                    break  # Success, exit retry loop
                else:
                    raise ValueError(f"Invalid result structure or empty translation")
                    
            except Exception as trans_error:
                logger.warning(f"Translation attempt {attempt + 1} failed: {type(trans_error).__name__}: {str(trans_error)[:100]}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                    logger.warning(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Translation failed after {max_retries} attempts")
                    return jsonify({
                        'success': False,
                        'error': 'Translation service is temporarily unavailable. Please try again in a moment.'
                    }), 503
        
        # Fallback: if result is still invalid, return error
        if result is None or not hasattr(result, 'text') or not result.text or not result.text.strip():
            logger.error(f"Translation returned invalid result after retries: {result}")
            return jsonify({
                'success': False,
                'error': 'Translation service returned an invalid response. Please try again.'
            }), 503
        
        translated_text = result.text.strip()
        
        if not translated_text:
            logger.error(f"Translation result was empty for: {text}")
            return jsonify({
                'success': False,
                'error': 'Translation service returned empty result. Please try again.'
            }), 503
        
        translation_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to database if available
        if DATABASE_AVAILABLE and translation_repo:
            try:
                user_id = None  # Anonymous user for now
                translation_repo.save_translation(
                    user_id=user_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    original_text=text,
                    translated_text=translated_text,
                    character_count=len(text),
                    translation_time_ms=translation_time_ms,
                    model_used='googletrans'
                )
            except Exception as db_error:
                logger.warning(f"Could not save translation to database: {db_error}")
        
        # Prepare response data
        response_data = {
            'success': True,
            'original_text': str(text) if text else '',
            'translated_text': str(translated_text) if translated_text else '',
            'source_lang': str(source_lang) if source_lang else '',
            'target_lang': str(target_lang) if target_lang else '',
            'source_lang_name': str(LANGUAGES.get(source_lang, '')),
            'target_lang_name': str(LANGUAGES.get(target_lang, '')),
            'translation_time_ms': int(translation_time_ms),
            'database_saved': DATABASE_AVAILABLE
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Translation failed: {str(e)}'
        }), 500

@app.route('/api/translate/batch', methods=['POST'])
def translate_batch():
    """
    Translate multiple texts at once
    
    Request body:
    {
        "texts": ["text1", "text2", ...],
        "source_lang": "en",
        "target_lang": "es"
    }
    """
    try:
        data = request.get_json()
        
        texts = data.get('texts', [])
        if not texts or not isinstance(texts, list):
            return jsonify({'success': False, 'error': 'texts must be a non-empty list'}), 400
        
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'es')
        
        if not validate_language_code(source_lang):
            return jsonify({'success': False, 'error': f'Invalid source language: {source_lang}'}), 400
        
        if not validate_language_code(target_lang):
            return jsonify({'success': False, 'error': f'Invalid target language: {target_lang}'}), 400
        
        translations = []
        for text in texts:
            try:
                result = translator.translate(text, src=source_lang, dest=target_lang)
                translations.append({
                    'original': text,
                    'translated': result.text
                })
            except Exception as e:
                logger.error(f"Error translating '{text}': {str(e)}")
                translations.append({
                    'original': text,
                    'translated': None,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'translations': translations,
            'count': len(translations),
            'source_lang': source_lang,
            'target_lang': target_lang
        }), 200
    
    except Exception as e:
        logger.error(f"Batch translation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Batch translation failed: {str(e)}'
        }), 500

@app.route('/api/speech/recognize', methods=['POST'])
def recognize_speech():
    """
    Recognize speech from audio file
    
    Request: multipart/form-data with 'audio' file and optional 'language' parameter
    """
    if not ENABLE_SPEECH_RECOGNITION:
        return jsonify({'success': False, 'error': 'Speech recognition is disabled'}), 403
    
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'Audio file is required'}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'en')
        
        if not validate_language_code(language):
            return jsonify({'success': False, 'error': f'Invalid language: {language}'}), 400
        
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No audio file selected'}), 400
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            
            recognized_text = recognizer.recognize_google(audio_data, language=language)
            
            return jsonify({
                'success': True,
                'recognized_text': recognized_text,
                'language': language,
                'language_name': LANGUAGES.get(language)
            }), 200
        
        except sr.UnknownValueError:
            return jsonify({
                'success': False,
                'error': 'Could not understand audio'
            }), 400
        
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Recognition service error: {str(e)}'
            }), 503
        
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Speech recognition error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to recognize speech: {str(e)}'
        }), 500

@app.route('/api/speech/synthesize', methods=['POST'])
def synthesize_speech():
    """
    Synthesize text to speech
    
    Request body:
    {
        "text": "text to synthesize",
        "language": "en",
        "slow": false (optional)
    }
    """
    if not ENABLE_TEXT_TO_SPEECH:
        return jsonify({'success': False, 'error': 'Text-to-speech is disabled'}), 403
    
    try:
        data = request.get_json()
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'Text field is required'}), 400
        
        language = data.get('language', 'en')
        slow = data.get('slow', False)
        
        if not validate_language_code(language):
            return jsonify({'success': False, 'error': f'Invalid language: {language}'}), 400
        
        # Generate audio
        tts = gTTS(text=text, lang=language, slow=slow)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return app.response_class(
            response=audio_buffer.getvalue(),
            status=200,
            mimetype='audio/mpeg',
            headers={'Content-Disposition': 'attachment; filename="speech.mp3"'}
        )
    
    except Exception as e:
        logger.error(f"Text-to-speech error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to synthesize speech: {str(e)}'
        }), 500

# ============ Database/History Endpoints ============

@app.route('/api/history', methods=['GET'])
def get_translation_history():
    """
    Get translation history for a user (currently returns all translations)
    
    Query parameters:
    - limit: number of records to return (default: 100)
    - offset: pagination offset (default: 0)
    """
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available',
            'message': 'Initialize database using: python init_db.py'
        }), 503
    
    try:
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # For now, use user_id = None (anonymous)
        user_id = None
        
        history = translation_repo.get_user_translations(user_id, limit, offset)
        
        # Convert datetime objects to strings
        for item in history:
            if 'created_at' in item and hasattr(item['created_at'], 'isoformat'):
                item['created_at'] = item['created_at'].isoformat()
            if 'updated_at' in item and hasattr(item['updated_at'], 'isoformat'):
                item['updated_at'] = item['updated_at'].isoformat()
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history),
            'limit': limit,
            'offset': offset
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve history: {str(e)}'
        }), 500

@app.route('/api/history/search', methods=['POST'])
def search_history():
    """
    Search translation history with full-text search
    
    Request body:
    {
        "query": "search text",
        "limit": 50 (optional)
    }
    """
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        limit = min(int(data.get('limit', 50)), 500)
        user_id = None
        
        results = translation_repo.search_translations(user_id, query, limit)
        
        # Convert datetime objects to strings
        for item in results:
            if 'created_at' in item and hasattr(item['created_at'], 'isoformat'):
                item['created_at'] = item['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/history/stats', methods=['GET'])
def get_translation_stats():
    """Get translation statistics"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_id = None
        stats = translation_repo.get_translation_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'count': len(stats)
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve stats: {str(e)}'
        }), 500

@app.route('/api/history/<int:translation_id>', methods=['DELETE'])
def delete_translation(translation_id):
    """Delete a specific translation"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_id = None
        success = translation_repo.delete_translation(translation_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Translation deleted successfully',
                'id': translation_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Translation not found'
            }), 404
    
    except Exception as e:
        logger.error(f"Error deleting translation: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete translation: {str(e)}'
        }), 500

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear all translation history"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        # Require confirmation via query parameter
        confirm = request.args.get('confirm', 'false').lower() == 'true'
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': 'Confirmation required. Add ?confirm=true to proceed'
            }), 400
        
        user_id = None
        deleted_count = translation_repo.clear_user_history(user_id)
        
        return jsonify({
            'success': True,
            'message': 'History cleared successfully',
            'deleted_count': deleted_count
        }), 200
    
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear history: {str(e)}'
        }), 500

@app.route('/api/database/status', methods=['GET'])
def database_status():
    """Check database connection status"""
    try:
        status = {
            'available': DATABASE_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        }
        
        if DATABASE_AVAILABLE and db and db.connection and db.connection.is_connected():
            # Try to get table count
            cursor = db.connection.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            cursor.close()
            
            status['tables_count'] = len(tables)
            status['tables'] = [table[0] for table in tables]
        
        return jsonify({
            'success': True,
            'database': status
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking database status: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Database check failed: {str(e)}'
        }), 500

# ============ Error Handlers ============

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ============ Main ============

if __name__ == '__main__':
    logger.info(f"Starting Language Translator API on {HOST}:{PORT}")
    logger.info(f"Environment: {FLASK_ENV}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"Database available: {DATABASE_AVAILABLE}")
    
    # Register cleanup on shutdown
    def shutdown_handler():
        logger.info("Shutting down...")
        if db and db.connection and db.connection.is_connected():
            db.close()
    
    import atexit
    atexit.register(shutdown_handler)
    
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=DEBUG
    )
