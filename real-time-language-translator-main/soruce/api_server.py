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
    DATABASE_AVAILABLE = True
    print(f"Database import successful: db={db}, translation_repo={translation_repo}")
except ImportError as e:
    print(f"Database import failed: {e}")
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Database module not available: {e}")
    db = None
    translation_repo = None
    DATABASE_AVAILABLE = False
except Exception as e:
    print(f"Unexpected error importing database: {e}")
    db = None
    translation_repo = None
    DATABASE_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request

# Enable CORS with proper configuration for authentication endpoints
CORS(app, resources={
    r"/api/*": {
        "origins": CORS_ORIGINS + ['http://localhost:3000', 'http://localhost:3001'],
        "methods": ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        "allow_headers": ['Content-Type', 'Authorization', 'X-User-Email'],
        "supports_credentials": True
    }
})

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
def initialize_database():
    """Initialize database connection and return status"""
    global DATABASE_AVAILABLE
    
    if db is not None:
        try:
            if db.create_database_if_not_exists():
                if db.connect():
                    db.create_tables()
                    DATABASE_AVAILABLE = True
                    logger.info("Database connected and initialized successfully")
                    return True
                else:
                    logger.warning("⚠ Could not connect to database - running in memory mode")
                    DATABASE_AVAILABLE = False
                    return False
            else:
                logger.warning("⚠ Could not create database - running in memory mode")
                DATABASE_AVAILABLE = False
                return False
        except Exception as e:
            logger.warning(f"⚠ Database initialization failed: {e} - running in memory mode")
            DATABASE_AVAILABLE = False
            return False
    else:
        logger.warning("⚠ Database module not available - running in memory mode")
        DATABASE_AVAILABLE = False
        return False

# Initialize database
initialize_database()

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
                # Get user email from request headers or use anonymous
                user_email = request.headers.get('X-User-Email') or data.get('user_email') or 'anonymous@translator.app'
                
                # Get client info
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent')
                
                # Create or get user
                user = translation_repo.create_or_get_user(user_email)
                
                if user:
                    # Save translation
                    translation_repo.save_translation(
                        user_email=user_email,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        original_text=text,
                        translated_text=translated_text,
                        translation_type='text',
                        character_count=len(text),
                        translation_time_ms=translation_time_ms,
                        confidence_score=getattr(result, 'confidence', 0.0) if result else 0.0,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    # Log API action
                    translation_repo.log_system_action(
                        user_email=user_email,
                        action='translate_text',
                        endpoint='/api/translate',
                        method='POST',
                        status_code=200,
                        response_time_ms=translation_time_ms,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_data={
                            'source_lang': source_lang,
                            'target_lang': target_lang,
                            'text_length': len(text)
                        }
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
            'character_count': len(text),
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

# ============ User Management API Endpoints ============

def is_database_available():
    """Check if database is available"""
    return DATABASE_AVAILABLE and db is not None and translation_repo is not None

@app.route('/api/debug/database', methods=['GET'])
def debug_database():
    """Debug database availability"""
    return jsonify({
        'DATABASE_AVAILABLE': DATABASE_AVAILABLE,
        'translation_repo_exists': translation_repo is not None,
        'db_exists': db is not None,
        'is_database_available': is_database_available(),
        'condition_check': not DATABASE_AVAILABLE or not translation_repo
    }), 200

@app.route('/api/users/profile', methods=['GET', 'POST'])
def user_profile():
    """Get or update user profile"""
    if not is_database_available():
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.json.get('user_email') if request.json else None
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or request body'
            }), 400
        
        if request.method == 'GET':
            # Get comprehensive user profile with statistics
            dashboard_data = translation_repo.get_user_dashboard_data(user_email)
            if dashboard_data:
                # Also get comprehensive statistics
                comprehensive_stats = translation_repo.get_comprehensive_user_statistics(user_email, '30')
                
                profile_data = {
                    'user_info': dashboard_data['user_info'],
                    'quick_stats': dashboard_data['quick_stats'],
                    'recent_activity': dashboard_data.get('recent_translations', [])[:5],  # Last 5 translations
                    'top_language_pairs': dashboard_data.get('top_language_pairs', []),
                    'statistics_summary': {
                        'last_30_days': {
                            'total_translations': comprehensive_stats['overall_statistics']['total_translations'] if comprehensive_stats else 0,
                            'total_characters': comprehensive_stats['overall_statistics']['total_characters'] if comprehensive_stats else 0,
                            'active_days': comprehensive_stats['overall_statistics']['active_days'] if comprehensive_stats else 0,
                            'avg_translation_time': comprehensive_stats['overall_statistics']['avg_translation_time_ms'] if comprehensive_stats else 0
                        } if comprehensive_stats else {}
                    }
                }
                
                return jsonify({
                    'success': True,
                    'profile': profile_data,
                    'generated_at': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
        
        elif request.method == 'POST':
            # Update user preferences
            data = request.get_json()
            source_lang = data.get('preferred_source_lang')
            target_lang = data.get('preferred_target_lang')
            full_name = data.get('full_name')
            
            if full_name:
                # Update full name
                cursor = db.connection.cursor()
                cursor.execute("UPDATE users SET full_name = %s WHERE email = %s", (full_name, user_email))
                db.connection.commit()
                cursor.close()
            
            if source_lang or target_lang:
                success = translation_repo.update_user_preferences(user_email, source_lang, target_lang)
                if not success:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update preferences'
                    }), 500
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            }), 200
    
    except Exception as e:
        logger.error(f"Error in user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Profile operation failed: {str(e)}'
        }), 500

@app.route('/api/users/history', methods=['GET'])
def user_history():
    """Get user's translation history with pagination"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or query parameters'
            }), 400
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        offset = (page - 1) * per_page
        
        # Get translation type filter
        translation_type = request.args.get('type')  # 'text' or 'speech'
        
        translations = translation_repo.get_user_translations(user_email, per_page, offset)
        
        return jsonify({
            'success': True,
            'translations': translations,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'has_more': len(translations) == per_page
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get history: {str(e)}'
        }), 500

@app.route('/api/users/history/search', methods=['GET'])
def search_user_history():
    """Search user's translation history"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        search_query = request.args.get('q', '').strip()
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or query parameters'
            }), 400
        
        if not search_query:
            return jsonify({
                'success': False,
                'error': 'Search query (q) is required'
            }), 400
        
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 results
        
        results = translation_repo.search_translations(user_email, search_query, limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'query': search_query,
            'count': len(results)
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching user history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/users/history/clear', methods=['POST'])
def clear_user_history():
    """Clear user's translation history"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.json.get('user_email') if request.json else None
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or request body'
            }), 400
        
        # Require confirmation
        confirm = request.args.get('confirm', 'false').lower() == 'true'
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': 'Confirmation required. Add ?confirm=true to proceed'
            }), 400
        
        # Delete user's translations
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM translations WHERE user_email = %s", (user_email,))
        deleted_count = cursor.rowcount
        
        # Reset user stats
        cursor.execute("""
            UPDATE users SET 
                total_translations = 0,
                total_characters = 0
            WHERE email = %s
        """, (user_email,))
        
        # Clear language stats
        cursor.execute("DELETE FROM user_language_stats WHERE user_email = %s", (user_email,))
        
        db.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'History cleared successfully',
            'deleted_count': deleted_count
        }), 200
    
    except Exception as e:
        logger.error(f"Error clearing user history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear history: {str(e)}'
        }), 500

@app.route('/api/users/statistics', methods=['GET'])
def get_user_statistics():
    """Get comprehensive user statistics including daily, weekly, monthly breakdowns"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or query parameters'
            }), 400
        
        # Get time period parameter (default: 30 days)
        period = request.args.get('period', '30').lower()
        if period not in ['7', '30', '90', 'all']:
            period = '30'
        
        stats = translation_repo.get_comprehensive_user_statistics(user_email, period)
        
        if stats:
            return jsonify({
                'success': True,
                'statistics': stats,
                'period': period,
                'generated_at': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User not found or no statistics available'
            }), 404
    
    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get statistics: {str(e)}'
        }), 500

@app.route('/api/users/analytics/daily', methods=['GET'])
def get_daily_analytics():
    """Get daily translation analytics for a user"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required'
            }), 400
        
        days = min(int(request.args.get('days', 30)), 365)  # Max 1 year
        
        analytics = translation_repo.get_daily_analytics(user_email, days)
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'days': days,
            'user_email': user_email
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting daily analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get daily analytics: {str(e)}'
        }), 500

@app.route('/api/users/analytics/languages', methods=['GET'])
def get_language_analytics():
    """Get language usage analytics for a user"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required'
            }), 400
        
        analytics = translation_repo.get_language_analytics(user_email)
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'user_email': user_email
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting language analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get language analytics: {str(e)}'
        }), 500

@app.route('/api/users/dashboard', methods=['GET'])
def get_user_dashboard():
    """Get comprehensive user dashboard data combining statistics, recent activity, and preferences"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or request.args.get('user_email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required'
            }), 400
        
        dashboard_data = translation_repo.get_user_dashboard_data(user_email)
        
        if dashboard_data:
            return jsonify({
                'success': True,
                'dashboard': dashboard_data,
                'generated_at': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
    
    except Exception as e:
        logger.error(f"Error getting user dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get dashboard data: {str(e)}'
        }), 500

# ============ User Management Endpoints ============

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        
        if not all([email, password, first_name, last_name]):
            return jsonify({
                'success': False, 
                'error': 'Email, password, firstName, and lastName are required'
            }), 400
        
        # Basic email validation
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        if DATABASE_AVAILABLE and translation_repo:
            try:
                # Check if user already exists
                existing_user = translation_repo.get_user_by_email(email)
                if existing_user:
                    return jsonify({'success': False, 'error': 'User already exists with this email'}), 409
                
                # Create user
                user_data = {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'password_hash': password  # In production, hash this!
                }
                
                user_id = translation_repo.create_user(user_data)
                
                if user_id:
                    # Get the created user
                    user = translation_repo.get_user_by_email(email)
                    logger.info(f"New user registered: {email}")
                    
                    return jsonify({
                        'success': True,
                        'message': 'User registered successfully',
                        'user': {
                            'id': str(user_id),
                            'email': user['email'],
                            'firstName': user['first_name'],
                            'lastName': user['last_name'],
                            'fullName': f"{user['first_name']} {user['last_name']}"
                        }
                    }), 201
                else:
                    return jsonify({'success': False, 'error': 'Failed to create user'}), 500
                    
            except Exception as e:
                logger.error(f"Database error during registration: {str(e)}")
                return jsonify({'success': False, 'error': 'Database error occurred'}), 500
        else:
            # Fallback: simulate user creation when database not available
            logger.warning("Database not available, simulating user registration")
            return jsonify({
                'success': True,
                'message': 'User registered successfully (simulation mode)',
                'user': {
                    'id': str(int(time.time())),
                    'email': email,
                    'firstName': first_name,
                    'lastName': last_name,
                    'fullName': f"{first_name} {last_name}"
                }
            }), 201
            
    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
        
        # Demo user check
        if email == 'demo@translator.com' and password == 'demo123':
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': '1',
                    'email': email,
                    'firstName': 'Demo',
                    'lastName': 'User',
                    'fullName': 'Demo User'
                }
            }), 200
        
        if is_database_available():
            try:
                user = translation_repo.get_user_by_email(email)
                if user and user.get('password_hash') == password:  # In production, use proper password hashing!
                    logger.info(f"User logged in: {email}")
                    return jsonify({
                        'success': True,
                        'message': 'Login successful',
                        'user': {
                            'id': user['email'],  # Use email as ID since it's the primary key
                            'email': user['email'],
                            'firstName': user['first_name'],
                            'lastName': user['last_name'],
                            'fullName': f"{user['first_name']} {user['last_name']}"
                        }
                    }), 200
                else:
                    return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
                    
            except Exception as e:
                logger.error(f"Database error during login: {str(e)}")
                return jsonify({'success': False, 'error': 'Login failed'}), 500
        else:
            return jsonify({'success': False, 'error': 'Authentication service unavailable'}), 503
            
    except Exception as e:
        logger.error(f"Error during user login: {str(e)}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500


# ============ User Preferences Management ============

@app.route('/api/users/preferences', methods=['GET', 'POST', 'PUT'])
def manage_user_preferences():
    """Manage user preferences - GET, POST, or PUT"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or (request.json.get('user_email') if request.json else None)
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or request body'
            }), 400
        
        if request.method == 'GET':
            # Get all user preferences
            preferences = translation_repo.get_all_user_preferences(user_email)
            return jsonify({
                'success': True,
                'preferences': preferences,
                'user_email': user_email
            }), 200
            
        elif request.method in ['POST', 'PUT']:
            # Set or update preferences
            data = request.json
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body is required'
                }), 400
            
            results = {}
            
            # Handle multiple preferences in one request
            if 'preferences' in data:
                for category, prefs in data['preferences'].items():
                    if not isinstance(prefs, dict):
                        continue
                    for key, value in prefs.items():
                        success = translation_repo.set_user_preference(user_email, key, value, category)
                        results[f"{category}.{key}"] = success
            
            # Handle single preference
            elif 'key' in data and 'value' in data:
                key = data['key']
                value = data['value']
                category = data.get('category', 'general')
                success = translation_repo.set_user_preference(user_email, key, value, category)
                results[key] = success
            
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid request format. Use "preferences" for bulk or "key"/"value" for single preference'
                }), 400
            
            return jsonify({
                'success': True,
                'updated_preferences': results,
                'user_email': user_email
            }), 200
        
    except Exception as e:
        logger.error(f"Error managing preferences: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to manage preferences: {str(e)}'
        }), 500


@app.route('/api/users/preferences/<preference_key>', methods=['GET', 'PUT', 'DELETE'])
def manage_single_preference(preference_key):
    """Manage a single user preference"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or (request.json.get('user_email') if request.json else None)
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required in headers (X-User-Email) or request body'
            }), 400
        
        if request.method == 'GET':
            # Get specific preference
            default_value = request.args.get('default')
            value = translation_repo.get_user_preference(user_email, preference_key, default_value)
            return jsonify({
                'success': True,
                'preference': {
                    'key': preference_key,
                    'value': value,
                    'user_email': user_email
                }
            }), 200
            
        elif request.method == 'PUT':
            # Update specific preference
            data = request.json
            if not data or 'value' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Request body with "value" field is required'
                }), 400
            
            value = data['value']
            category = data.get('category', 'general')
            success = translation_repo.set_user_preference(user_email, preference_key, value, category)
            
            return jsonify({
                'success': success,
                'preference': {
                    'key': preference_key,
                    'value': value,
                    'category': category
                }
            }), 200 if success else 500
        
        # Note: DELETE functionality would require adding a delete method to the repository
        
    except Exception as e:
        logger.error(f"Error managing single preference: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to manage preference: {str(e)}'
        }), 500


@app.route('/api/users/favorites/language-pairs', methods=['GET', 'POST'])
def manage_favorite_language_pairs():
    """Manage user's favorite language pairs"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or (request.json.get('user_email') if request.json else None)
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required'
            }), 400
        
        if request.method == 'GET':
            # Get user's language pair statistics including favorites
            analytics = translation_repo.get_language_analytics(user_email)
            
            # Filter for favorite pairs
            favorite_pairs = [
                pair for pair in analytics.get('language_pairs', [])
                if pair.get('is_favorite', False)
            ]
            
            return jsonify({
                'success': True,
                'favorite_pairs': favorite_pairs,
                'all_pairs': analytics.get('language_pairs', [])
            }), 200
            
        elif request.method == 'POST':
            # Set favorite language pair
            data = request.json
            if not data or 'language_pair' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Request body with "language_pair" field is required'
                }), 400
            
            language_pair = data['language_pair']
            is_favorite = data.get('is_favorite', True)
            
            success = translation_repo.set_favorite_language_pair(user_email, language_pair, is_favorite)
            
            return jsonify({
                'success': success,
                'language_pair': language_pair,
                'is_favorite': is_favorite
            }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error managing favorite language pairs: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to manage favorites: {str(e)}'
        }), 500


@app.route('/api/users/profile/sync', methods=['POST'])
def sync_user_profile():
    """Sync user profile data after login to ensure all data is persistent"""
    if not DATABASE_AVAILABLE or not translation_repo:
        return jsonify({
            'success': False,
            'error': 'Database is not available'
        }), 503
    
    try:
        user_email = request.headers.get('X-User-Email') or (request.json.get('user_email') if request.json else None)
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'User email is required'
            }), 400
        
        # Get comprehensive user data
        dashboard_data = translation_repo.get_user_dashboard_data(user_email)
        
        if dashboard_data:
            # Set default preferences if they don't exist
            preferences = dashboard_data.get('user_preferences', {})
            
            # Initialize default preferences if none exist
            if not preferences:
                default_prefs = {
                    'ui': {
                        'theme': 'light',
                        'language': 'en',
                        'auto_speak': False,
                        'show_confidence': True
                    },
                    'translation': {
                        'auto_detect': True,
                        'save_history': True,
                        'max_history_items': 100
                    },
                    'audio': {
                        'enable_tts': True,
                        'speech_rate': 'normal',
                        'voice_preference': 'default'
                    },
                    'privacy': {
                        'analytics_enabled': True,
                        'share_anonymous_stats': True
                    }
                }
                
                # Set default preferences
                for category, prefs in default_prefs.items():
                    for key, value in prefs.items():
                        translation_repo.set_user_preference(user_email, key, value, category)
                
                # Refresh dashboard data to include the new preferences
                dashboard_data = translation_repo.get_user_dashboard_data(user_email)
            
            return jsonify({
                'success': True,
                'profile_data': dashboard_data,
                'synced_at': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User profile not found'
            }), 404
        
    except Exception as e:
        logger.error(f"Error syncing user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to sync profile: {str(e)}'
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
        use_reloader=False  # Temporarily disable reloader to fix database import issue
    )
