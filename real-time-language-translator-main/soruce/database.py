"""
MySQL Database Connection and Models for Language Translator
Handles all database operations and schema creation
"""

import mysql.connector
from mysql.connector import Error, errorcode
from datetime import datetime
import logging
from config import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, 
    DB_NAME, DB_CHARSET, DB_COLLATE
)

logger = logging.getLogger(__name__)

class Database:
    """Handles MySQL database connection and operations"""
    
    def __init__(self):
        self.connection = None
        self.host = DB_HOST
        self.port = DB_PORT
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.database = DB_NAME
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=DB_CHARSET,
                autocommit=True,
                use_unicode=True
            )
            logger.info(f"Connected to MySQL database: {self.database}")
            return True
        except Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error("Invalid MySQL credentials")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error(f"Database '{self.database}' does not exist")
            else:
                logger.error(f"Database connection error: {err}")
            return False
    
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist"""
        try:
            # Connect without specifying database
            conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Create database
            create_db_query = f"""
            CREATE DATABASE IF NOT EXISTS `{self.database}`
            CHARACTER SET {DB_CHARSET}
            COLLATE {DB_COLLATE};
            """
            cursor.execute(create_db_query)
            logger.info(f"Database '{self.database}' created or already exists")
            
            cursor.close()
            conn.close()
            return True
        except Error as err:
            logger.error(f"Error creating database: {err}")
            return False
    
    def create_tables(self):
        """Create all necessary tables with email-based user management"""
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return False
        
        cursor = self.connection.cursor()
        
        tables = {
            'users': """
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR(255) PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255),
                preferred_source_lang VARCHAR(10) DEFAULT 'en',
                preferred_target_lang VARCHAR(10) DEFAULT 'es',
                is_active BOOLEAN DEFAULT TRUE,
                total_translations INT DEFAULT 0,
                total_characters INT DEFAULT 0,
                last_login TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_created_at (created_at),
                INDEX idx_last_login (last_login)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'translations': """
            CREATE TABLE IF NOT EXISTS translations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                source_language VARCHAR(10) NOT NULL,
                target_language VARCHAR(10) NOT NULL,
                original_text LONGTEXT NOT NULL,
                translated_text LONGTEXT NOT NULL,
                translation_type ENUM('text', 'speech') DEFAULT 'text',
                character_count INT DEFAULT 0,
                translation_time_ms INT DEFAULT 0,
                confidence_score FLOAT DEFAULT 0.0,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
                INDEX idx_user_email (user_email),
                INDEX idx_created_at (created_at),
                INDEX idx_lang_pair (source_language, target_language),
                INDEX idx_type (translation_type),
                INDEX idx_user_date (user_email, created_at),
                FULLTEXT INDEX ft_original (original_text),
                FULLTEXT INDEX ft_translated (translated_text)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'user_sessions': """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
                INDEX idx_user_email (user_email),
                INDEX idx_token (session_token),
                INDEX idx_expires (expires_at),
                INDEX idx_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'user_language_stats': """
            CREATE TABLE IF NOT EXISTS user_language_stats (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                language_pair VARCHAR(21) NOT NULL,
                translation_count INT DEFAULT 0,
                character_count INT DEFAULT 0,
                avg_translation_time FLOAT DEFAULT 0.0,
                total_translation_time INT DEFAULT 0,
                avg_confidence_score FLOAT DEFAULT 0.0,
                favorite_pair BOOLEAN DEFAULT FALSE,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
                UNIQUE KEY unique_user_pair (user_email, language_pair),
                INDEX idx_user_email (user_email),
                INDEX idx_language_pair (language_pair),
                INDEX idx_last_used (last_used),
                INDEX idx_favorite (favorite_pair)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'user_preferences': """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                preference_key VARCHAR(100) NOT NULL,
                preference_value JSON,
                category ENUM('ui', 'translation', 'audio', 'general', 'privacy') DEFAULT 'general',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
                UNIQUE KEY unique_user_preference (user_email, preference_key),
                INDEX idx_user_email (user_email),
                INDEX idx_category (category),
                INDEX idx_preference_key (preference_key)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'system_logs': """
            CREATE TABLE IF NOT EXISTS system_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255),
                action VARCHAR(100) NOT NULL,
                endpoint VARCHAR(255),
                method VARCHAR(10),
                status_code INT,
                response_time_ms INT,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                error_message TEXT,
                request_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE SET NULL ON UPDATE CASCADE,
                INDEX idx_user_email (user_email),
                INDEX idx_action (action),
                INDEX idx_created_at (created_at),
                INDEX idx_status_code (status_code),
                INDEX idx_endpoint (endpoint)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE)
        }
        
        for table_name, create_table_sql in tables.items():
            try:
                cursor.execute(create_table_sql)
                logger.info(f"Table '{table_name}' created or already exists")
            except Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    logger.info(f"Table '{table_name}' already exists")
                else:
                    logger.error(f"Error creating table '{table_name}': {err}")
                    cursor.close()
                    return False
        
        cursor.close()
        return True
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")


class TranslationRepository:
    """Repository for translation operations with email-based user management"""
    
    def __init__(self, db):
        self.db = db
    
    def create_or_get_user(self, email, full_name=None, password_hash=None):
        """Create a new user or get existing user by email"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                # Update last login
                cursor.execute("UPDATE users SET last_login = NOW() WHERE email = %s", (email,))
                self.db.connection.commit()
                cursor.close()
                return user
            else:
                # Create new user
                query = """
                INSERT INTO users (email, full_name, password_hash, last_login)
                VALUES (%s, %s, %s, NOW())
                """
                cursor.execute(query, (email, full_name or email.split('@')[0], password_hash))
                self.db.connection.commit()
                
                # Get the created user
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                logger.info(f"New user created: {email}")
                return user
                
        except Error as err:
            logger.error(f"Error creating/getting user: {err}")
            return None
    
    def save_translation(self, user_email, source_lang, target_lang, original_text, 
                        translated_text, translation_type='text', character_count=0, 
                        translation_time_ms=0, confidence_score=0.0, ip_address=None, user_agent=None):
        """Save translation to database"""
        try:
            cursor = self.db.connection.cursor()
            
            # Insert translation
            query = """
            INSERT INTO translations 
            (user_email, source_language, target_language, original_text, translated_text, 
             translation_type, character_count, translation_time_ms, confidence_score, 
             ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                user_email, source_lang, target_lang, original_text, translated_text,
                translation_type, character_count, translation_time_ms, confidence_score,
                ip_address, user_agent
            ))
            
            # Update user stats
            cursor.execute("""
                UPDATE users SET 
                    total_translations = total_translations + 1,
                    total_characters = total_characters + %s
                WHERE email = %s
            """, (character_count, user_email))
            
            # Update or create language stats with enhanced metrics
            language_pair = f"{source_lang}-{target_lang}"
            cursor.execute("""
                INSERT INTO user_language_stats 
                (user_email, language_pair, translation_count, character_count, 
                 avg_translation_time, total_translation_time, avg_confidence_score, last_used)
                VALUES (%s, %s, 1, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    translation_count = translation_count + 1,
                    character_count = character_count + VALUES(character_count),
                    avg_translation_time = (avg_translation_time * (translation_count - 1) + %s) / translation_count,
                    total_translation_time = total_translation_time + %s,
                    avg_confidence_score = (avg_confidence_score * (translation_count - 1) + %s) / translation_count,
                    last_used = NOW()
            """, (user_email, language_pair, character_count, translation_time_ms, 
                  translation_time_ms, confidence_score, translation_time_ms, 
                  translation_time_ms, confidence_score))
            
            self.db.connection.commit()
            translation_id = cursor.lastrowid
            cursor.close()
            logger.info(f"Translation saved with ID: {translation_id} for user: {user_email}")
            return translation_id
            
        except Error as err:
            logger.error(f"Error saving translation: {err}")
            return None
    
    def get_user_translations(self, user_email, limit=100, offset=0):
        """Get user's translation history"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM translations 
            WHERE user_email = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (user_email, limit, offset))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as err:
            logger.error(f"Error retrieving translations: {err}")
            return []
    
    def get_user_stats(self, user_email):
        """Get comprehensive user statistics"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Get basic user stats
            cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
            user_stats = cursor.fetchone()
            
            # Get language pair stats
            cursor.execute("""
                SELECT language_pair, translation_count, character_count, last_used
                FROM user_language_stats 
                WHERE user_email = %s 
                ORDER BY translation_count DESC
            """, (user_email,))
            language_stats = cursor.fetchall()
            
            # Get recent activity
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as translations, SUM(character_count) as characters
                FROM translations 
                WHERE user_email = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (user_email,))
            recent_activity = cursor.fetchall()
            
            cursor.close()
            
            return {
                'user': user_stats,
                'language_pairs': language_stats,
                'recent_activity': recent_activity
            }
            
        except Error as err:
            logger.error(f"Error retrieving user stats: {err}")
            return None
    
    def search_translations(self, user_email, search_text, limit=50):
        """Search user's translations with full-text search"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM translations 
            WHERE user_email = %s 
            AND (MATCH(original_text) AGAINST(%s IN BOOLEAN MODE) 
                 OR MATCH(translated_text) AGAINST(%s IN BOOLEAN MODE))
            ORDER BY created_at DESC 
            LIMIT %s
            """
            cursor.execute(query, (user_email, search_text, search_text, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as err:
            logger.error(f"Error searching translations: {err}")
            return []
    
    def update_user_preferences(self, user_email, source_lang=None, target_lang=None):
        """Update user's language preferences"""
        try:
            cursor = self.db.connection.cursor()
            updates = []
            values = []
            
            if source_lang:
                updates.append("preferred_source_lang = %s")
                values.append(source_lang)
            
            if target_lang:
                updates.append("preferred_target_lang = %s")
                values.append(target_lang)
            
            if updates:
                values.append(user_email)
                query = f"UPDATE users SET {', '.join(updates)} WHERE email = %s"
                cursor.execute(query, values)
                self.db.connection.commit()
            
            cursor.close()
            return True
            
        except Error as err:
            logger.error(f"Error updating preferences: {err}")
            return False
    
    def create_user(self, user_data):
        """Create a new user"""
        try:
            cursor = self.db.connection.cursor()
            query = """
            INSERT INTO users (email, full_name, password_hash, preferred_source_lang, preferred_target_lang)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                user_data['email'],
                f"{user_data['first_name']} {user_data['last_name']}",
                user_data['password_hash'],
                user_data.get('preferred_source_lang', 'en'),
                user_data.get('preferred_target_lang', 'es')
            ))
            self.db.connection.commit()
            user_email = user_data['email']
            cursor.close()
            logger.info(f"User created successfully: {user_email}")
            return user_email
            
        except Error as err:
            logger.error(f"Error creating user: {err}")
            return None
    
    def get_user_by_email(self, email):
        """Get user by email address"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                # Split full_name into first_name and last_name for compatibility
                name_parts = user['full_name'].split(' ', 1)
                user['first_name'] = name_parts[0]
                user['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
                
            return user
            
        except Error as err:
            logger.error(f"Error getting user by email: {err}")
            return None
    
    def log_system_action(self, user_email, action, endpoint=None, method=None, 
                         status_code=None, response_time_ms=None, ip_address=None, 
                         user_agent=None, error_message=None, request_data=None):
        """Log system actions and API calls"""
        try:
            cursor = self.db.connection.cursor()
            query = """
            INSERT INTO system_logs 
            (user_email, action, endpoint, method, status_code, response_time_ms, 
             ip_address, user_agent, error_message, request_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                user_email, action, endpoint, method, status_code, response_time_ms,
                ip_address, user_agent, error_message, request_data
            ))
            self.db.connection.commit()
            cursor.close()
            return True
            
        except Error as err:
            logger.error(f"Error logging action: {err}")
            return False
    
    def get_comprehensive_user_statistics(self, user_email, period='30'):
        """Get comprehensive user statistics with time-based analysis"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Determine time filter
            if period == 'all':
                time_filter = ""
                time_params = ()
            else:
                days = int(period)
                time_filter = "AND t.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
                time_params = (days,)
            
            # Get basic user info
            cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return None
            
            # Get overall statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_translations,
                    SUM(character_count) as total_characters,
                    AVG(character_count) as avg_characters_per_translation,
                    AVG(translation_time_ms) as avg_translation_time_ms,
                    COUNT(DISTINCT source_language) as unique_source_languages,
                    COUNT(DISTINCT target_language) as unique_target_languages,
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    MIN(created_at) as first_translation,
                    MAX(created_at) as last_translation
                FROM translations t
                WHERE user_email = %s {time_filter}
            """, (user_email,) + time_params)
            
            overall_stats = cursor.fetchone()
            
            # Get daily activity breakdown
            cursor.execute(f"""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as translations,
                    SUM(character_count) as characters,
                    AVG(translation_time_ms) as avg_time_ms,
                    COUNT(DISTINCT CONCAT(source_language, '-', target_language)) as language_pairs
                FROM translations t
                WHERE user_email = %s {time_filter}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 90
            """, (user_email,) + time_params)
            
            daily_activity = cursor.fetchall()
            
            # Get hourly patterns
            cursor.execute(f"""
                SELECT 
                    HOUR(created_at) as hour,
                    COUNT(*) as translations,
                    SUM(character_count) as characters
                FROM translations t
                WHERE user_email = %s {time_filter}
                GROUP BY HOUR(created_at)
                ORDER BY hour
            """, (user_email,) + time_params)
            
            hourly_patterns = cursor.fetchall()
            
            # Get top language pairs
            cursor.execute(f"""
                SELECT 
                    CONCAT(source_language, '-', target_language) as language_pair,
                    COUNT(*) as count,
                    SUM(character_count) as total_characters,
                    AVG(character_count) as avg_characters,
                    MAX(created_at) as last_used
                FROM translations t
                WHERE user_email = %s {time_filter}
                GROUP BY source_language, target_language
                ORDER BY count DESC
                LIMIT 20
            """, (user_email,) + time_params)
            
            language_pairs = cursor.fetchall()
            
            # Get performance metrics
            cursor.execute(f"""
                SELECT 
                    translation_type,
                    COUNT(*) as count,
                    AVG(translation_time_ms) as avg_time_ms,
                    AVG(character_count) as avg_characters,
                    AVG(confidence_score) as avg_confidence
                FROM translations t
                WHERE user_email = %s {time_filter}
                GROUP BY translation_type
            """, (user_email,) + time_params)
            
            performance_by_type = cursor.fetchall()
            
            cursor.close()
            
            # Convert datetime objects to ISO format
            for activity in daily_activity:
                if activity['date']:
                    activity['date'] = activity['date'].isoformat()
            
            for pair in language_pairs:
                if pair['last_used']:
                    pair['last_used'] = pair['last_used'].isoformat()
            
            if overall_stats['first_translation']:
                overall_stats['first_translation'] = overall_stats['first_translation'].isoformat()
            if overall_stats['last_translation']:
                overall_stats['last_translation'] = overall_stats['last_translation'].isoformat()
            
            return {
                'user_info': {
                    'email': user_info['email'],
                    'full_name': user_info['full_name'],
                    'preferred_source_lang': user_info['preferred_source_lang'],
                    'preferred_target_lang': user_info['preferred_target_lang'],
                    'member_since': user_info['created_at'].isoformat() if user_info['created_at'] else None,
                    'last_login': user_info['last_login'].isoformat() if user_info['last_login'] else None
                },
                'overall_statistics': overall_stats,
                'daily_activity': daily_activity,
                'hourly_patterns': hourly_patterns,
                'top_language_pairs': language_pairs,
                'performance_by_type': performance_by_type
            }
            
        except Error as err:
            logger.error(f"Error getting comprehensive statistics: {err}")
            return None
    
    def get_daily_analytics(self, user_email, days=30):
        """Get detailed daily analytics for user activity"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Get daily statistics with trend analysis
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as translations,
                    SUM(character_count) as characters,
                    AVG(character_count) as avg_characters,
                    AVG(translation_time_ms) as avg_time_ms,
                    COUNT(DISTINCT source_language) as source_languages_used,
                    COUNT(DISTINCT target_language) as target_languages_used,
                    COUNT(DISTINCT HOUR(created_at)) as active_hours,
                    MIN(created_at) as first_translation_time,
                    MAX(created_at) as last_translation_time
                FROM translations
                WHERE user_email = %s 
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (user_email, days))
            
            daily_data = cursor.fetchall()
            
            # Calculate trends
            if len(daily_data) > 1:
                recent_avg = sum(d['translations'] for d in daily_data[:7]) / min(7, len(daily_data))
                older_avg = sum(d['translations'] for d in daily_data[7:14]) / min(7, len(daily_data[7:14])) if len(daily_data) > 7 else recent_avg
                trend = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend = 0
            
            cursor.close()
            
            # Convert datetime objects
            for day_data in daily_data:
                if day_data['date']:
                    day_data['date'] = day_data['date'].isoformat()
                if day_data['first_translation_time']:
                    day_data['first_translation_time'] = day_data['first_translation_time'].isoformat()
                if day_data['last_translation_time']:
                    day_data['last_translation_time'] = day_data['last_translation_time'].isoformat()
            
            return {
                'daily_data': daily_data,
                'summary': {
                    'total_days': len(daily_data),
                    'active_days': len([d for d in daily_data if d['translations'] > 0]),
                    'total_translations': sum(d['translations'] for d in daily_data),
                    'total_characters': sum(d['characters'] for d in daily_data),
                    'avg_translations_per_day': sum(d['translations'] for d in daily_data) / len(daily_data) if daily_data else 0,
                    'trend_percentage': round(trend, 2)
                }
            }
            
        except Error as err:
            logger.error(f"Error getting daily analytics: {err}")
            return {'daily_data': [], 'summary': {}}
    
    def get_language_analytics(self, user_email):
        """Get comprehensive language usage analytics"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Get source language statistics
            cursor.execute("""
                SELECT 
                    source_language,
                    COUNT(*) as usage_count,
                    SUM(character_count) as total_characters,
                    AVG(character_count) as avg_characters,
                    AVG(translation_time_ms) as avg_time_ms,
                    MAX(created_at) as last_used
                FROM translations
                WHERE user_email = %s
                GROUP BY source_language
                ORDER BY usage_count DESC
            """, (user_email,))
            
            source_languages = cursor.fetchall()
            
            # Get target language statistics
            cursor.execute("""
                SELECT 
                    target_language,
                    COUNT(*) as usage_count,
                    SUM(character_count) as total_characters,
                    AVG(character_count) as avg_characters,
                    AVG(translation_time_ms) as avg_time_ms,
                    MAX(created_at) as last_used
                FROM translations
                WHERE user_email = %s
                GROUP BY target_language
                ORDER BY usage_count DESC
            """, (user_email,))
            
            target_languages = cursor.fetchall()
            
            # Get language pair combinations with detailed stats
            cursor.execute("""
                SELECT 
                    source_language,
                    target_language,
                    CONCAT(source_language, ' → ', target_language) as language_pair,
                    COUNT(*) as usage_count,
                    SUM(character_count) as total_characters,
                    AVG(character_count) as avg_characters,
                    AVG(translation_time_ms) as avg_time_ms,
                    AVG(confidence_score) as avg_confidence,
                    MIN(created_at) as first_used,
                    MAX(created_at) as last_used,
                    COUNT(DISTINCT DATE(created_at)) as days_used
                FROM translations
                WHERE user_email = %s
                GROUP BY source_language, target_language
                ORDER BY usage_count DESC
            """, (user_email,))
            
            language_pairs = cursor.fetchall()
            
            cursor.close()
            
            # Add language names from LANGUAGES dict
            from googletrans import LANGUAGES
            
            for lang_stat in source_languages + target_languages:
                lang_code = lang_stat.get('source_language') or lang_stat.get('target_language')
                lang_stat['language_name'] = LANGUAGES.get(lang_code, lang_code.title())
                if lang_stat['last_used']:
                    lang_stat['last_used'] = lang_stat['last_used'].isoformat()
            
            for pair in language_pairs:
                pair['source_language_name'] = LANGUAGES.get(pair['source_language'], pair['source_language'].title())
                pair['target_language_name'] = LANGUAGES.get(pair['target_language'], pair['target_language'].title())
                if pair['first_used']:
                    pair['first_used'] = pair['first_used'].isoformat()
                if pair['last_used']:
                    pair['last_used'] = pair['last_used'].isoformat()
            
            return {
                'source_languages': source_languages,
                'target_languages': target_languages,
                'language_pairs': language_pairs,
                'summary': {
                    'unique_source_languages': len(source_languages),
                    'unique_target_languages': len(target_languages),
                    'unique_language_pairs': len(language_pairs),
                    'most_used_source': source_languages[0]['source_language'] if source_languages else None,
                    'most_used_target': target_languages[0]['target_language'] if target_languages else None,
                    'most_used_pair': language_pairs[0]['language_pair'] if language_pairs else None
                }
            }
            
        except Error as err:
            logger.error(f"Error getting language analytics: {err}")
            return {'source_languages': [], 'target_languages': [], 'language_pairs': [], 'summary': {}}
    
    def set_user_preference(self, user_email, key, value, category='general'):
        """Set or update a user preference"""
        try:
            cursor = self.db.connection.cursor()
            
            # Convert value to JSON if it's not a string
            import json
            if not isinstance(value, str):
                json_value = json.dumps(value)
            else:
                json_value = json.dumps(value)
            
            query = """
            INSERT INTO user_preferences (user_email, preference_key, preference_value, category)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                preference_value = VALUES(preference_value),
                category = VALUES(category),
                updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(query, (user_email, key, json_value, category))
            self.db.connection.commit()
            cursor.close()
            return True
            
        except Error as err:
            logger.error(f"Error setting preference: {err}")
            return False
    
    def get_user_preference(self, user_email, key, default_value=None):
        """Get a specific user preference"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT preference_value FROM user_preferences 
            WHERE user_email = %s AND preference_key = %s AND is_active = TRUE
            """
            cursor.execute(query, (user_email, key))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                import json
                return json.loads(result['preference_value'])
            return default_value
            
        except Error as err:
            logger.error(f"Error getting preference: {err}")
            return default_value
    
    def get_all_user_preferences(self, user_email):
        """Get all preferences for a user organized by category"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT preference_key, preference_value, category
            FROM user_preferences 
            WHERE user_email = %s AND is_active = TRUE
            ORDER BY category, preference_key
            """
            cursor.execute(query, (user_email,))
            results = cursor.fetchall()
            cursor.close()
            
            # Organize preferences by category
            preferences = {}
            import json
            for row in results:
                category = row['category']
                if category not in preferences:
                    preferences[category] = {}
                preferences[category][row['preference_key']] = json.loads(row['preference_value'])
            
            return preferences
            
        except Error as err:
            logger.error(f"Error getting all preferences: {err}")
            return {}
    
    def set_favorite_language_pair(self, user_email, language_pair, is_favorite=True):
        """Mark a language pair as favorite for quick access"""
        try:
            cursor = self.db.connection.cursor()
            
            if is_favorite:
                # First, remove favorite status from all other pairs for this user
                cursor.execute("""
                    UPDATE user_language_stats 
                    SET favorite_pair = FALSE 
                    WHERE user_email = %s
                """, (user_email,))
            
            # Update the specific pair
            cursor.execute("""
                UPDATE user_language_stats 
                SET favorite_pair = %s 
                WHERE user_email = %s AND language_pair = %s
            """, (is_favorite, user_email, language_pair))
            
            self.db.connection.commit()
            cursor.close()
            return True
            
        except Error as err:
            logger.error(f"Error setting favorite language pair: {err}")
            return False
    
    def get_user_dashboard_data(self, user_email):
        """Get all data needed for user dashboard in a single call"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            
            # Get user basic info
            cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return None
            
            # Get recent translations (last 10)
            cursor.execute("""
                SELECT id, source_language, target_language, original_text, translated_text, 
                       character_count, translation_time_ms, created_at
                FROM translations
                WHERE user_email = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_email,))
            
            recent_translations = cursor.fetchall()
            
            # Get today's statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as today_translations,
                    SUM(character_count) as today_characters
                FROM translations
                WHERE user_email = %s 
                AND DATE(created_at) = CURDATE()
            """, (user_email,))
            
            today_stats = cursor.fetchone()
            
            # Get this week's statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as week_translations,
                    SUM(character_count) as week_characters,
                    COUNT(DISTINCT DATE(created_at)) as active_days_this_week
                FROM translations
                WHERE user_email = %s 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, (user_email,))
            
            week_stats = cursor.fetchone()
            
            # Get top 5 language pairs with favorite status
            cursor.execute("""
                SELECT 
                    CONCAT(t.source_language, ' → ', t.target_language) as pair,
                    COUNT(*) as count,
                    COALESCE(uls.favorite_pair, FALSE) as is_favorite,
                    COALESCE(uls.avg_translation_time, 0) as avg_time,
                    COALESCE(uls.avg_confidence_score, 0) as avg_confidence
                FROM translations t
                LEFT JOIN user_language_stats uls ON uls.user_email = t.user_email 
                    AND uls.language_pair = CONCAT(t.source_language, '-', t.target_language)
                WHERE t.user_email = %s
                GROUP BY t.source_language, t.target_language
                ORDER BY count DESC
                LIMIT 5
            """, (user_email,))
            
            top_pairs = cursor.fetchall()
            
            # Get user preferences
            prefs_cursor = self.db.connection.cursor(dictionary=True)
            prefs_cursor.execute("""
                SELECT preference_key, preference_value, category
                FROM user_preferences 
                WHERE user_email = %s AND is_active = TRUE
            """, (user_email,))
            
            preferences_raw = prefs_cursor.fetchall()
            prefs_cursor.close()
            
            # Organize preferences
            import json
            user_preferences = {}
            for pref in preferences_raw:
                category = pref['category']
                if category not in user_preferences:
                    user_preferences[category] = {}
                user_preferences[category][pref['preference_key']] = json.loads(pref['preference_value'])
            
            cursor.close()
            
            # Convert datetime objects
            for trans in recent_translations:
                if trans['created_at']:
                    trans['created_at'] = trans['created_at'].isoformat()
            
            return {
                'user_info': {
                    'email': user_info['email'],
                    'full_name': user_info['full_name'],
                    'preferred_source_lang': user_info['preferred_source_lang'],
                    'preferred_target_lang': user_info['preferred_target_lang'],
                    'total_translations': user_info['total_translations'] or 0,
                    'total_characters': user_info['total_characters'] or 0,
                    'member_since': user_info['created_at'].isoformat() if user_info['created_at'] else None,
                    'last_login': user_info['last_login'].isoformat() if user_info['last_login'] else None
                },
                'quick_stats': {
                    'today': today_stats,
                    'this_week': week_stats
                },
                'recent_translations': recent_translations,
                'top_language_pairs': top_pairs,
                'user_preferences': user_preferences,
                'has_personalized_settings': len(user_preferences) > 0
            }
            
        except Error as err:
            logger.error(f"Error getting dashboard data: {err}")
            return None


# Initialize database connection
db = Database()
translation_repo = TranslationRepository(db)