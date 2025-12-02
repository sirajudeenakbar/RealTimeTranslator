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
        """Create all necessary tables"""
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return False
        
        cursor = self.connection.cursor()
        
        tables = {
            'users': """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_username (username),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'translation_history': """
            CREATE TABLE IF NOT EXISTS translation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                source_language VARCHAR(10) NOT NULL,
                target_language VARCHAR(10) NOT NULL,
                original_text LONGTEXT NOT NULL,
                translated_text LONGTEXT NOT NULL,
                character_count INT,
                translation_time_ms INT,
                model_used VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_lang_pair (source_language, target_language),
                FULLTEXT INDEX ft_original (original_text),
                FULLTEXT INDEX ft_translated (translated_text)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'speech_records': """
            CREATE TABLE IF NOT EXISTS speech_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                source_language VARCHAR(10) NOT NULL,
                target_language VARCHAR(10) NOT NULL,
                original_audio LONGBLOB,
                transcribed_text LONGTEXT,
                translated_text LONGTEXT,
                duration_seconds FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_lang_pair (source_language, target_language)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'language_preferences': """
            CREATE TABLE IF NOT EXISTS language_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                preferred_source_lang VARCHAR(10) DEFAULT 'en',
                preferred_target_lang VARCHAR(10) DEFAULT 'es',
                favorite_language_pairs JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'translations_stats': """
            CREATE TABLE IF NOT EXISTS translations_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                total_translations INT DEFAULT 0,
                total_characters INT DEFAULT 0,
                favorite_source_lang VARCHAR(10),
                favorite_target_lang VARCHAR(10),
                last_translation_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET={} COLLATE={};
            """.format(DB_CHARSET, DB_COLLATE),
            
            'api_logs': """
            CREATE TABLE IF NOT EXISTS api_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                endpoint VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                status_code INT,
                response_time_ms INT,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                request_params JSON,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_endpoint (endpoint),
                INDEX idx_created_at (created_at),
                INDEX idx_status_code (status_code)
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
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")


class TranslationRepository:
    """Repository for translation history operations"""
    
    def __init__(self, db):
        self.db = db
    
    def save_translation(self, user_id, source_lang, target_lang, original_text, 
                        translated_text, character_count=0, translation_time_ms=0, model_used='googletrans'):
        """Save translation to database"""
        try:
            cursor = self.db.connection.cursor()
            query = """
            INSERT INTO translation_history 
            (user_id, source_language, target_language, original_text, translated_text, 
             character_count, translation_time_ms, model_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                user_id, source_lang, target_lang, original_text, translated_text,
                character_count, translation_time_ms, model_used
            ))
            self.db.connection.commit()
            translation_id = cursor.lastrowid
            cursor.close()
            logger.info(f"Translation saved with ID: {translation_id}")
            return translation_id
        except Error as err:
            logger.error(f"Error saving translation: {err}")
            return None
    
    def get_user_translations(self, user_id, limit=100, offset=0):
        """Get user's translation history"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM translation_history 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (user_id, limit, offset))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as err:
            logger.error(f"Error retrieving translations: {err}")
            return []
    
    def get_translation_stats(self, user_id):
        """Get translation statistics for a user"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT 
                COUNT(*) as total_translations,
                SUM(character_count) as total_characters,
                AVG(translation_time_ms) as avg_time_ms,
                MAX(created_at) as last_translation_date,
                source_language,
                target_language
            FROM translation_history 
            WHERE user_id = %s
            GROUP BY source_language, target_language
            ORDER BY total_translations DESC
            """
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as err:
            logger.error(f"Error retrieving stats: {err}")
            return []
    
    def search_translations(self, user_id, search_text, limit=50):
        """Search user's translations with full-text search"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM translation_history 
            WHERE user_id = %s 
            AND (MATCH(original_text) AGAINST(%s IN BOOLEAN MODE) 
                 OR MATCH(translated_text) AGAINST(%s IN BOOLEAN MODE))
            ORDER BY created_at DESC 
            LIMIT %s
            """
            cursor.execute(query, (user_id, search_text, search_text, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as err:
            logger.error(f"Error searching translations: {err}")
            return []
    
    def delete_translation(self, translation_id, user_id):
        """Delete a translation record"""
        try:
            cursor = self.db.connection.cursor()
            query = "DELETE FROM translation_history WHERE id = %s AND user_id = %s"
            cursor.execute(query, (translation_id, user_id))
            self.db.connection.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Error as err:
            logger.error(f"Error deleting translation: {err}")
            return False
    
    def clear_user_history(self, user_id):
        """Clear all translations for a user"""
        try:
            cursor = self.db.connection.cursor()
            query = "DELETE FROM translation_history WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            self.db.connection.commit()
            deleted_count = cursor.rowcount
            cursor.close()
            logger.info(f"Cleared {deleted_count} translations for user {user_id}")
            return deleted_count
        except Error as err:
            logger.error(f"Error clearing history: {err}")
            return 0


# Initialize database connection
db = Database()
translation_repo = TranslationRepository(db)
