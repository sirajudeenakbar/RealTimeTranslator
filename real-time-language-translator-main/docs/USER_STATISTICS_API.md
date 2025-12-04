# User Statistics and History API Documentation

This document describes the comprehensive user statistics and history system implemented in the Real-Time Language Translator API.

## Overview

The system now provides detailed user analytics, statistics, and history tracking organized within user data. All endpoints require user authentication via the `X-User-Email` header.

## API Endpoints

### 1. User Dashboard
**GET** `/api/users/dashboard`

Returns comprehensive dashboard data combining user info, quick stats, recent translations, and top language pairs.

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "dashboard": {
    "user_info": {
      "email": "user@example.com",
      "full_name": "John Doe",
      "preferred_source_lang": "en",
      "preferred_target_lang": "es",
      "total_translations": 245,
      "total_characters": 15420,
      "member_since": "2023-01-15T10:30:00",
      "last_login": "2023-12-03T14:25:30"
    },
    "quick_stats": {
      "today": {
        "today_translations": 5,
        "today_characters": 320
      },
      "this_week": {
        "week_translations": 28,
        "week_characters": 1850,
        "active_days_this_week": 4
      }
    },
    "recent_translations": [
      {
        "id": 1001,
        "source_language": "en",
        "target_language": "es",
        "original_text": "Hello, how are you?",
        "translated_text": "Hola, ¿cómo estás?",
        "character_count": 18,
        "translation_time_ms": 245,
        "created_at": "2023-12-03T14:20:00"
      }
    ],
    "top_language_pairs": [
      {
        "pair": "en → es",
        "count": 89
      },
      {
        "pair": "en → fr",
        "count": 67
      }
    ]
  }
}
```

### 2. Comprehensive Statistics
**GET** `/api/users/statistics`

Returns detailed statistics with time-based analysis, daily activity, hourly patterns, and performance metrics.

**Query Parameters:**
- `period`: Time period for analysis (`7`, `30`, `90`, `all`) - default: `30`

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "user_info": {
      "email": "user@example.com",
      "full_name": "John Doe",
      "preferred_source_lang": "en",
      "preferred_target_lang": "es",
      "member_since": "2023-01-15T10:30:00",
      "last_login": "2023-12-03T14:25:30"
    },
    "overall_statistics": {
      "total_translations": 245,
      "total_characters": 15420,
      "avg_characters_per_translation": 62.9,
      "avg_translation_time_ms": 312.5,
      "unique_source_languages": 3,
      "unique_target_languages": 5,
      "active_days": 22,
      "first_translation": "2023-01-15T11:00:00",
      "last_translation": "2023-12-03T14:20:00"
    },
    "daily_activity": [
      {
        "date": "2023-12-03",
        "translations": 5,
        "characters": 320,
        "avg_time_ms": 280.4,
        "language_pairs": 2
      }
    ],
    "hourly_patterns": [
      {
        "hour": 9,
        "translations": 25,
        "characters": 1650
      },
      {
        "hour": 14,
        "translations": 32,
        "characters": 2180
      }
    ],
    "top_language_pairs": [
      {
        "language_pair": "en-es",
        "count": 89,
        "total_characters": 5680,
        "avg_characters": 63.8,
        "last_used": "2023-12-03T14:20:00"
      }
    ],
    "performance_by_type": [
      {
        "translation_type": "text",
        "count": 240,
        "avg_time_ms": 305.2,
        "avg_characters": 62.5,
        "avg_confidence": 0.95
      }
    ]
  }
}
```

### 3. Daily Analytics
**GET** `/api/users/analytics/daily`

Returns detailed daily analytics with trend analysis.

**Query Parameters:**
- `days`: Number of days to analyze (max: 365) - default: `30`

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "analytics": {
    "daily_data": [
      {
        "date": "2023-12-03",
        "translations": 5,
        "characters": 320,
        "avg_characters": 64.0,
        "avg_time_ms": 280.4,
        "source_languages_used": 1,
        "target_languages_used": 2,
        "active_hours": 3,
        "first_translation_time": "2023-12-03T09:15:00",
        "last_translation_time": "2023-12-03T14:20:00"
      }
    ],
    "summary": {
      "total_days": 30,
      "active_days": 22,
      "total_translations": 245,
      "total_characters": 15420,
      "avg_translations_per_day": 8.2,
      "trend_percentage": 15.3
    }
  }
}
```

### 4. Language Analytics
**GET** `/api/users/analytics/languages`

Returns comprehensive language usage analytics including source languages, target languages, and language pairs.

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "analytics": {
    "source_languages": [
      {
        "source_language": "en",
        "language_name": "English",
        "usage_count": 200,
        "total_characters": 12800,
        "avg_characters": 64.0,
        "avg_time_ms": 310.5,
        "last_used": "2023-12-03T14:20:00"
      }
    ],
    "target_languages": [
      {
        "target_language": "es",
        "language_name": "Spanish",
        "usage_count": 89,
        "total_characters": 5680,
        "avg_characters": 63.8,
        "avg_time_ms": 295.2,
        "last_used": "2023-12-03T14:20:00"
      }
    ],
    "language_pairs": [
      {
        "source_language": "en",
        "target_language": "es",
        "source_language_name": "English",
        "target_language_name": "Spanish",
        "language_pair": "en → es",
        "usage_count": 89,
        "total_characters": 5680,
        "avg_characters": 63.8,
        "avg_time_ms": 295.2,
        "avg_confidence": 0.96,
        "first_used": "2023-01-15T11:00:00",
        "last_used": "2023-12-03T14:20:00",
        "days_used": 18
      }
    ],
    "summary": {
      "unique_source_languages": 3,
      "unique_target_languages": 5,
      "unique_language_pairs": 8,
      "most_used_source": "en",
      "most_used_target": "es",
      "most_used_pair": "en → es"
    }
  }
}
```

### 5. User History
**GET** `/api/users/history`

Returns paginated user translation history.

**Query Parameters:**
- `page`: Page number - default: `1`
- `per_page`: Items per page (max: 100) - default: `20`
- `type`: Translation type filter (`text`, `speech`) - optional

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "translations": [
    {
      "id": 1001,
      "user_email": "user@example.com",
      "source_language": "en",
      "target_language": "es",
      "original_text": "Hello, how are you?",
      "translated_text": "Hola, ¿cómo estás?",
      "translation_type": "text",
      "character_count": 18,
      "translation_time_ms": 245,
      "confidence_score": 0.96,
      "ip_address": "192.168.1.100",
      "created_at": "2023-12-03T14:20:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "has_more": true
  }
}
```

### 6. Search History
**GET** `/api/users/history/search`

Search user's translation history using full-text search.

**Query Parameters:**
- `q`: Search query (required)
- `limit`: Max results (max: 100) - default: `50`

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": 1001,
      "source_language": "en",
      "target_language": "es",
      "original_text": "Hello, how are you?",
      "translated_text": "Hola, ¿cómo estás?",
      "character_count": 18,
      "created_at": "2023-12-03T14:20:00"
    }
  ],
  "query": "hello",
  "count": 1
}
```

### 7. Enhanced User Profile
**GET** `/api/users/profile`

Returns comprehensive user profile with embedded statistics.

**Headers:**
```
X-User-Email: user@example.com
```

**Response:**
```json
{
  "success": true,
  "profile": {
    "user_info": {
      "email": "user@example.com",
      "full_name": "John Doe",
      "preferred_source_lang": "en",
      "preferred_target_lang": "es",
      "total_translations": 245,
      "total_characters": 15420,
      "member_since": "2023-01-15T10:30:00",
      "last_login": "2023-12-03T14:25:30"
    },
    "quick_stats": {
      "today": {
        "today_translations": 5,
        "today_characters": 320
      },
      "this_week": {
        "week_translations": 28,
        "week_characters": 1850,
        "active_days_this_week": 4
      }
    },
    "recent_activity": [
      {
        "id": 1001,
        "source_language": "en",
        "target_language": "es",
        "original_text": "Hello, how are you?",
        "translated_text": "Hola, ¿cómo estás?",
        "character_count": 18,
        "translation_time_ms": 245,
        "created_at": "2023-12-03T14:20:00"
      }
    ],
    "top_language_pairs": [
      {
        "pair": "en → es",
        "count": 89
      }
    ],
    "statistics_summary": {
      "last_30_days": {
        "total_translations": 245,
        "total_characters": 15420,
        "active_days": 22,
        "avg_translation_time": 312.5
      }
    }
  }
}
```

### 8. Clear User History
**POST** `/api/users/history/clear?confirm=true`

Clears all user translation history and resets statistics.

**Query Parameters:**
- `confirm`: Must be `true` to proceed

**Headers:**
```
X-User-Email: user@example.com
Content-Type: application/json
```

**Response:**
```json
{
  "success": true,
  "message": "History cleared successfully",
  "deleted_count": 245
}
```

## Database Schema Updates

The system uses the following key database tables:

### users
- Stores user information, preferences, and aggregate statistics
- Fields: `email`, `full_name`, `preferred_source_lang`, `preferred_target_lang`, `total_translations`, `total_characters`, `last_login`, `created_at`, `updated_at`

### translations
- Stores individual translation records with full details
- Fields: `id`, `user_email`, `source_language`, `target_language`, `original_text`, `translated_text`, `translation_type`, `character_count`, `translation_time_ms`, `confidence_score`, `ip_address`, `user_agent`, `created_at`

### user_language_stats
- Tracks usage statistics per language pair per user
- Fields: `user_email`, `language_pair`, `translation_count`, `character_count`, `last_used`, `created_at`, `updated_at`

### system_logs
- Logs all API actions and system events
- Fields: `user_email`, `action`, `endpoint`, `method`, `status_code`, `response_time_ms`, `ip_address`, `user_agent`, `error_message`, `request_data`, `created_at`

## Frontend Integration

To integrate these endpoints in your frontend:

1. **Authentication**: Always include `X-User-Email` header with requests
2. **Dashboard**: Use `/api/users/dashboard` for main user dashboard
3. **Analytics Page**: Combine `/api/users/statistics` and `/api/users/analytics/daily` for detailed analytics
4. **History Page**: Use `/api/users/history` with pagination for translation history
5. **Language Analytics**: Use `/api/users/analytics/languages` for language usage insights

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message describing the issue"
}
```

Common error status codes:
- `400`: Bad Request (missing parameters, invalid data)
- `401`: Unauthorized (missing or invalid user email)
- `404`: Not Found (user or resource not found)
- `503`: Service Unavailable (database not available)

## Performance Considerations

- Statistics are calculated in real-time but can be cached for better performance
- Large datasets are paginated to prevent memory issues
- Database indexes are optimized for common query patterns
- Full-text search is available on translation content

## Testing

Use the provided test script `test_user_statistics.py` to verify all endpoints work correctly:

```bash
python test_user_statistics.py
```

This will create sample translations and test all statistics endpoints.