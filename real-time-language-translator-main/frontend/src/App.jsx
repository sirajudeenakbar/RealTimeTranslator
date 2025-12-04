import React, { useState, useEffect, useRef } from 'react';
import { Globe, Send, History, User, Menu, X, Trash2, Download, Settings, Type, Copy, Check, Mic, Volume2, StopCircle, AlertCircle, LogOut } from 'lucide-react';
import LoginPage from './LoginPage';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const LanguageTranslator = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('es');
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentView, setCurrentView] = useState('chat');
  const [history, setHistory] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [userName, setUserName] = useState('Guest User');
  const [userEmail, setUserEmail] = useState('guest@translator.com');
  const [textInput, setTextInput] = useState('');
  const [textOutput, setTextOutput] = useState('');
  const [copied, setCopied] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioTranscript, setAudioTranscript] = useState('');
  const [audioTranslation, setAudioTranslation] = useState('');
  const [error, setError] = useState('');
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [apiStatus, setApiStatus] = useState('disconnected');
  const [lastTranslationTime, setLastTranslationTime] = useState(0);
  const [nextTranslationReadyTime, setNextTranslationReadyTime] = useState(0);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const lastTranslationTimeRef = useRef(0);
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Check if user is logged in on mount
  useEffect(() => {
    const user = localStorage.getItem('user');
    const authToken = localStorage.getItem('authToken');
    
    if (user && authToken) {
      try {
        const userData = JSON.parse(user);
        setIsAuthenticated(true);
        setCurrentUser(userData);
        setUserName(userData.fullName || userData.firstName || 'User');
        setUserEmail(userData.email || 'user@translator.com');
        
        // Sync user profile data from server
        syncUserProfile(userData.email);
        
        // Load user's translation history and preferences
        loadUserHistory(userData.email);
        
      } catch (err) {
        console.error('Error parsing user data:', err);
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
      }
    }
  }, []);

  // Function to sync user profile with server
  const syncUserProfile = async (email) => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/profile/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': email
        },
        body: JSON.stringify({ user_email: email })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.profile_data) {
          // Apply user preferences to UI
          const prefs = data.profile_data.user_preferences;
          
          // Set language preferences if they exist
          if (prefs?.translation?.preferred_source_lang) {
            setSourceLang(prefs.translation.preferred_source_lang);
          }
          if (prefs?.translation?.preferred_target_lang) {
            setTargetLang(prefs.translation.preferred_target_lang);
          }
          
          console.log('User profile synced successfully');
        }
      } else if (response.status === 404) {
        // User profile not found, this is expected for new users
        console.log('New user detected, profile will be created on first translation');
      } else {
        console.warn('Profile sync failed with status:', response.status);
      }
    } catch (error) {
      console.error('Error syncing user profile:', error);
      // Continue without profile sync - not critical for basic functionality
    }
  };

  // Function to load user's translation history
  const loadUserHistory = async (email) => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/history?per_page=20`, {
        headers: {
          'X-User-Email': email
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.translations) {
          // Convert server format to app format
          const formattedHistory = data.translations.map(t => ({
            id: t.id,
            text: t.original_text,
            translation: t.translated_text,
            sourceLang: t.source_language,
            targetLang: t.target_language,
            timestamp: new Date(t.created_at)
          }));
          
          setHistory(formattedHistory);
          console.log(`Loaded ${formattedHistory.length} translations from history`);
        }
      } else if (response.status === 404) {
        // No history found - normal for new users
        console.log('No translation history found for user');
      }
    } catch (error) {
      console.error('Error loading user history:', error);
      // Continue without history - not critical for basic functionality
    }
  };

  // Function to save user preferences
  const saveUserPreference = async (key, value, category = 'general') => {
    if (!currentUser?.email) return;

    try {
      const response = await fetch(`${API_BASE_URL}/users/preferences/${key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': currentUser.email
        },
        body: JSON.stringify({
          value: value,
          category: category
        })
      });

      if (response.ok) {
        console.log(`Preference ${key} saved successfully`);
      }
    } catch (error) {
      console.error('Error saving preference:', error);
    }
  };

  // Function to handle language change and save preference
  const handleSourceLangChange = (lang) => {
    setSourceLang(lang);
    saveUserPreference('preferred_source_lang', lang, 'translation');
  };

  const handleTargetLangChange = (lang) => {
    setTargetLang(lang);
    saveUserPreference('preferred_target_lang', lang, 'translation');
  };

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'ru', name: 'Russian' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
    { code: 'zh', name: 'Chinese (Simplified)' },
    { code: 'zh-tw', name: 'Chinese (Traditional)' },
    { code: 'ar', name: 'Arabic' },
    { code: 'hi', name: 'Hindi' },
    { code: 'bn', name: 'Bengali' },
    { code: 'ta', name: 'Tamil' },
    { code: 'te', name: 'Telugu' },
    { code: 'ml', name: 'Malayalam' },
    { code: 'kn', name: 'Kannada' },
    { code: 'gu', name: 'Gujarati' },
    { code: 'mr', name: 'Marathi' },
    { code: 'pa', name: 'Punjabi' },
    { code: 'ur', name: 'Urdu' },
    { code: 'si', name: 'Sinhala' },
    { code: 'th', name: 'Thai' },
    { code: 'vi', name: 'Vietnamese' },
    { code: 'id', name: 'Indonesian' },
    { code: 'ms', name: 'Malay' },
    { code: 'tl', name: 'Filipino' },
    { code: 'sw', name: 'Swahili' },
    { code: 'tr', name: 'Turkish' },
    { code: 'pl', name: 'Polish' },
    { code: 'nl', name: 'Dutch' },
    { code: 'sv', name: 'Swedish' },
    { code: 'da', name: 'Danish' },
    { code: 'no', name: 'Norwegian' },
    { code: 'fi', name: 'Finnish' },
    { code: 'is', name: 'Icelandic' },
    { code: 'cs', name: 'Czech' },
    { code: 'sk', name: 'Slovak' },
    { code: 'hu', name: 'Hungarian' },
    { code: 'ro', name: 'Romanian' },
    { code: 'bg', name: 'Bulgarian' },
    { code: 'hr', name: 'Croatian' },
    { code: 'sr', name: 'Serbian' },
    { code: 'sl', name: 'Slovenian' },
    { code: 'lt', name: 'Lithuanian' },
    { code: 'lv', name: 'Latvian' },
    { code: 'et', name: 'Estonian' },
    { code: 'uk', name: 'Ukrainian' },
    { code: 'be', name: 'Belarusian' },
    { code: 'ka', name: 'Georgian' },
    { code: 'am', name: 'Amharic' },
    { code: 'he', name: 'Hebrew' },
    { code: 'fa', name: 'Persian' },
    { code: 'ps', name: 'Pashto' },
    { code: 'ku', name: 'Kurdish' },
    { code: 'az', name: 'Azerbaijani' },
    { code: 'uz', name: 'Uzbek' },
    { code: 'kk', name: 'Kazakh' },
    { code: 'ky', name: 'Kyrgyz' },
    { code: 'tg', name: 'Tajik' },
    { code: 'mn', name: 'Mongolian' },
    { code: 'my', name: 'Myanmar (Burmese)' },
    { code: 'km', name: 'Khmer' },
    { code: 'lo', name: 'Lao' },
    { code: 'ne', name: 'Nepali' },
    { code: 'dz', name: 'Dzongkha' },
    { code: 'bo', name: 'Tibetan' },
    { code: 'yo', name: 'Yoruba' },
    { code: 'ig', name: 'Igbo' },
    { code: 'ha', name: 'Hausa' },
    { code: 'zu', name: 'Zulu' },
    { code: 'xh', name: 'Xhosa' },
    { code: 'af', name: 'Afrikaans' },
    { code: 'sq', name: 'Albanian' },
    { code: 'eu', name: 'Basque' },
    { code: 'ca', name: 'Catalan' },
    { code: 'gl', name: 'Galician' },
    { code: 'cy', name: 'Welsh' },
    { code: 'ga', name: 'Irish' },
    { code: 'gd', name: 'Scottish Gaelic' },
    { code: 'mt', name: 'Maltese' },
    { code: 'is', name: 'Icelandic' },
    { code: 'fo', name: 'Faroese' }
  ];

  // Initialize API connection and fetch available languages
  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          setApiStatus('connected');
          // Fetch available languages from backend
          const langResponse = await fetch(`${API_BASE_URL}/languages`);
          if (langResponse.ok) {
            const data = await langResponse.json();
            if (data.success && data.languages) {
              setAvailableLanguages(data.languages);
            }
          }
        } else {
          setApiStatus('disconnected');
          setError('Backend API is not responding properly');
        }
      } catch (err) {
        setApiStatus('disconnected');
        console.error('API connection error:', err);
      }
    };

    checkApiStatus();
    // Check API status every 30 seconds
    const interval = setInterval(checkApiStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const translateText = async (text) => {
    setIsTranslating(true);
    setError('');
    
    try {
      if (apiStatus !== 'connected') {
        throw new Error('Backend API is not available. Please ensure the server is running.');
      }

      // Get user email for API call
      const currentUserEmail = currentUser?.email || 'anonymous@translator.app';

      const response = await fetch(`${API_BASE_URL}/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': currentUserEmail
        },
        body: JSON.stringify({
          text: text,
          source_lang: sourceLang,
          target_lang: targetLang,
          user_email: currentUserEmail,
          translation_type: 'text'
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Translation failed');
      }

      if (data.success) {
        return data.translated_text;
      } else {
        throw new Error(data.error || 'Translation failed');
      }
    } catch (error) {
      console.error('Translation error:', error);
      const errorMsg = error.message || 'Translation error. Please try again.';
      setError(errorMsg);
      return `Error: ${errorMsg}`;
    } finally {
      setIsTranslating(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    // Rate limiting check using ref for immediate feedback
    const now = Date.now();
    const timeSinceLastTranslation = now - lastTranslationTimeRef.current;
    const RATE_LIMIT_MS = 20000; // 20 seconds - buffer to avoid Google Translate rate limiting

    if (timeSinceLastTranslation < RATE_LIMIT_MS) {
      const waitTime = Math.ceil((RATE_LIMIT_MS - timeSinceLastTranslation) / 1000);
      setError(`Please wait ${waitTime} seconds before translating again (rate limiting)`);
      return;
    }

    // Update rate limiting timestamp IMMEDIATELY (before translation starts)
    lastTranslationTimeRef.current = now;
    setLastTranslationTime(now);
    setNextTranslationReadyTime(now + 20000);

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: input,
      lang: sourceLang,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');

    const translation = await translateText(input);

    const botMessage = {
      id: Date.now() + 1,
      type: 'bot',
      text: translation,
      lang: targetLang,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, botMessage]);
    
    const historyItem = {
      id: Date.now(),
      original: input,
      translated: translation,
      from: sourceLang,
      to: targetLang,
      date: new Date().toLocaleDateString(),
      time: new Date().toLocaleTimeString()
    };
    
    setHistory(prev => [historyItem, ...prev]);
  };

  const clearHistory = () => {
    setHistory([]);
  };

  const clearChat = () => {
    setMessages([]);
  };

  const downloadHistory = () => {
    const content = history.map(item => 
      `[${item.date} ${item.time}]\nFrom: ${item.from} → To: ${item.to}\nOriginal: ${item.original}\nTranslated: ${item.translated}\n\n`
    ).join('---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'translation-history.txt';
    a.click();
  };

  const handleTextTranslate = async () => {
    if (!textInput.trim()) return;

    // Rate limiting check using ref for immediate feedback
    const now = Date.now();
    const timeSinceLastTranslation = now - lastTranslationTimeRef.current;
    const RATE_LIMIT_MS = 20000; // 20 seconds - buffer to avoid Google Translate rate limiting

    if (timeSinceLastTranslation < RATE_LIMIT_MS) {
      const waitTime = Math.ceil((RATE_LIMIT_MS - timeSinceLastTranslation) / 1000);
      setError(`Please wait ${waitTime} seconds before translating again (rate limiting)`);
      return;
    }

    // Update rate limiting timestamp IMMEDIATELY (before translation starts)
    lastTranslationTimeRef.current = now;
    setLastTranslationTime(now);
    setNextTranslationReadyTime(now + 20000);

    setIsTranslating(true);
    const translation = await translateText(textInput);
    setTextOutput(translation);
    setIsTranslating(false);

    const historyItem = {
      id: Date.now(),
      original: textInput,
      translated: translation,
      from: sourceLang,
      to: targetLang,
      date: new Date().toLocaleDateString(),
      time: new Date().toLocaleTimeString()
    };
    
    setHistory(prev => [historyItem, ...prev]);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(textOutput);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const swapLanguages = () => {
    const newSourceLang = targetLang;
    const newTargetLang = sourceLang;
    
    setSourceLang(newSourceLang);
    setTargetLang(newTargetLang);
    setTextInput(textOutput);
    setTextOutput(textInput);
    
    // Save preferences for the swapped languages
    if (currentUser?.email) {
      saveUserPreference('preferred_source_lang', newSourceLang, 'translation');
      saveUserPreference('preferred_target_lang', newTargetLang, 'translation');
    }
  };

  const getLanguageCode = (lang) => {
    const langMap = {
      'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE',
      'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'ja': 'ja-JP',
      'ko': 'ko-KR', 'zh': 'zh-CN', 'zh-tw': 'zh-TW', 'ar': 'ar-SA', 
      'hi': 'hi-IN', 'bn': 'bn-BD', 'ta': 'ta-IN', 'te': 'te-IN',
      'ml': 'ml-IN', 'kn': 'kn-IN', 'gu': 'gu-IN', 'mr': 'mr-IN',
      'pa': 'pa-IN', 'ur': 'ur-PK', 'si': 'si-LK', 'th': 'th-TH',
      'vi': 'vi-VN', 'id': 'id-ID', 'ms': 'ms-MY', 'tl': 'tl-PH',
      'sw': 'sw-KE', 'tr': 'tr-TR', 'pl': 'pl-PL', 'nl': 'nl-NL',
      'sv': 'sv-SE', 'da': 'da-DK', 'no': 'no-NO', 'fi': 'fi-FI',
      'is': 'is-IS', 'cs': 'cs-CZ', 'sk': 'sk-SK', 'hu': 'hu-HU',
      'ro': 'ro-RO', 'bg': 'bg-BG', 'hr': 'hr-HR', 'sr': 'sr-RS',
      'sl': 'sl-SI', 'lt': 'lt-LT', 'lv': 'lv-LV', 'et': 'et-EE',
      'uk': 'uk-UA', 'be': 'be-BY', 'ka': 'ka-GE', 'am': 'am-ET',
      'he': 'he-IL', 'fa': 'fa-IR', 'ps': 'ps-AF', 'ku': 'ku-TR',
      'az': 'az-AZ', 'uz': 'uz-UZ', 'kk': 'kk-KZ', 'ky': 'ky-KG',
      'tg': 'tg-TJ', 'mn': 'mn-MN', 'my': 'my-MM', 'km': 'km-KH',
      'lo': 'lo-LA', 'ne': 'ne-NP', 'dz': 'dz-BT', 'bo': 'bo-CN',
      'yo': 'yo-NG', 'ig': 'ig-NG', 'ha': 'ha-NG', 'zu': 'zu-ZA',
      'xh': 'xh-ZA', 'af': 'af-ZA', 'sq': 'sq-AL', 'eu': 'eu-ES',
      'ca': 'ca-ES', 'gl': 'gl-ES', 'cy': 'cy-GB', 'ga': 'ga-IE',
      'gd': 'gd-GB', 'mt': 'mt-MT', 'fo': 'fo-FO'
    };
    return langMap[lang] || 'en-US';
  };

  const startRecording = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      setError('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    // Clear previous errors and transcript
    setError('');
    setAudioTranscript('');
    setAudioTranslation('');

    try {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      // Configure recognition
      recognition.continuous = false;  // Changed to false for better control
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = getLanguageCode(sourceLang);
      
      let finalTranscript = '';
      let interimTranscript = '';

      recognition.onstart = () => {
        setIsRecording(true);
        setError('');
        console.log('Speech recognition started');
      };

      recognition.onresult = (event) => {
        finalTranscript = '';
        interimTranscript = '';
        
        for (let i = 0; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        const currentTranscript = finalTranscript || interimTranscript;
        setAudioTranscript(currentTranscript);
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        
        switch (event.error) {
          case 'no-speech':
            setError('No speech detected. Please try again and speak clearly.');
            break;
          case 'audio-capture':
            setError('Microphone access denied or not available.');
            break;
          case 'not-allowed':
            setError('Microphone permission denied. Please allow microphone access.');
            break;
          case 'network':
            setError('Network error. Please check your internet connection.');
            break;
          case 'service-not-allowed':
            setError('Speech recognition service not available.');
            break;
          default:
            setError(`Speech recognition error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
        console.log('Speech recognition ended');
        
        // If we have a transcript, automatically translate it
        if (finalTranscript.trim()) {
          handleVoiceTranslation(finalTranscript.trim());
        } else if (interimTranscript.trim()) {
          handleVoiceTranslation(interimTranscript.trim());
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
      
      // Set a timeout to auto-stop after 10 seconds
      setTimeout(() => {
        if (recognitionRef.current && isRecording) {
          recognition.stop();
        }
      }, 10000);
      
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      setError('Failed to start speech recognition. Please try again.');
      setIsRecording(false);
    }
  };

  const handleVoiceTranslation = async (transcript) => {
    if (!transcript.trim()) return;
    
    try {
      setIsTranslating(true);
      const translation = await translateText(transcript);
      setAudioTranslation(translation);
      
      // Add to history
      const historyItem = {
        id: Date.now(),
        original: transcript,
        translated: translation,
        from: sourceLang,
        to: targetLang,
        date: new Date().toLocaleDateString(),
        time: new Date().toLocaleTimeString()
      };
      
      setHistory(prev => [historyItem, ...prev]);
    } catch (error) {
      console.error('Translation error:', error);
      setError('Translation failed. Please try again.');
    } finally {
      setIsTranslating(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
  };

  const speakText = (text, lang) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === 'en' ? 'en-US' : 
                       lang === 'es' ? 'es-ES' :
                       lang === 'fr' ? 'fr-FR' :
                       lang === 'de' ? 'de-DE' :
                       lang === 'it' ? 'it-IT' :
                       lang === 'pt' ? 'pt-PT' :
                       lang === 'ru' ? 'ru-RU' :
                       lang === 'ja' ? 'ja-JP' :
                       lang === 'ko' ? 'ko-KR' :
                       lang === 'zh' ? 'zh-CN' :
                       lang === 'ar' ? 'ar-SA' :
                       lang === 'hi' ? 'hi-IN' : 'en-US';
      
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      window.speechSynthesis.speak(utterance);
    } else {
      alert('Text-to-speech is not supported in your browser.');
    }
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
    setCurrentUser(null);
    setUserName('Guest User');
    setUserEmail('guest@translator.com');
    setMessages([]);
    setHistory([]);
    setCurrentView('chat');
  };

  const handleLoginSuccess = (userData) => {
    setIsAuthenticated(true);
    setCurrentUser(userData);
    setUserName(userData.fullName);
    setUserEmail(userData.email);
  };

  // If not authenticated, show login page
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLoginSuccess} />;
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 p-3 flex items-start space-x-2">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-800">{error}</p>
          </div>
          <button
            onClick={() => setError('')}
            className="text-red-600 hover:text-red-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* API Status Banner */}
      {apiStatus !== 'connected' && (
        <div className="bg-yellow-50 border border-yellow-200 p-2 flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-yellow-600 rounded-full animate-pulse"></div>
            <span className="text-yellow-800">Backend API: Connecting...</span>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white shadow-md px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Globe className="w-8 h-8 text-indigo-600" />
          <h1 className="text-xl font-bold text-gray-800">TranslatePro</h1>
          <div className="flex items-center space-x-1 ml-4">
            <div className={`w-2 h-2 rounded-full ${apiStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-600">{apiStatus === 'connected' ? 'Connected' : 'Offline'}</span>
          </div>
        </div>
        
        <nav className="hidden md:flex space-x-4">
          <button
            onClick={() => setCurrentView('text')}
            className={`px-4 py-2 rounded-lg transition flex items-center space-x-2 ${
              currentView === 'text' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Type className="w-4 h-4" />
            <span>Text</span>
          </button>
          <button
            onClick={() => setCurrentView('voice')}
            className={`px-4 py-2 rounded-lg transition flex items-center space-x-2 ${
              currentView === 'voice' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Mic className="w-4 h-4" />
            <span>Voice</span>
          </button>
          <button
            onClick={() => setCurrentView('chat')}
            className={`px-4 py-2 rounded-lg transition ${
              currentView === 'chat' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setCurrentView('history')}
            className={`px-4 py-2 rounded-lg transition flex items-center space-x-2 ${
              currentView === 'history' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <History className="w-4 h-4" />
            <span>History</span>
          </button>
          <button
            onClick={() => setCurrentView('account')}
            className={`px-4 py-2 rounded-lg transition flex items-center space-x-2 ${
              currentView === 'account' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Account</span>
          </button>
          <button
            onClick={handleLogout}
            className="px-4 py-2 rounded-lg text-gray-600 hover:bg-red-50 hover:text-red-600 transition flex items-center space-x-2"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </nav>

        <button 
          className="md:hidden"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </header>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden bg-white shadow-lg p-4 space-y-2">
          <button
            onClick={() => { setCurrentView('text'); setMenuOpen(false); }}
            className={`w-full px-4 py-2 rounded-lg text-left flex items-center space-x-2 ${
              currentView === 'text' ? 'bg-indigo-600 text-white' : 'text-gray-600'
            }`}
          >
            <Type className="w-4 h-4" />
            <span>Text Translator</span>
          </button>
          <button
            onClick={() => { setCurrentView('voice'); setMenuOpen(false); }}
            className={`w-full px-4 py-2 rounded-lg text-left flex items-center space-x-2 ${
              currentView === 'voice' ? 'bg-indigo-600 text-white' : 'text-gray-600'
            }`}
          >
            <Mic className="w-4 h-4" />
            <span>Voice Translator</span>
          </button>
          <button
            onClick={() => { setCurrentView('chat'); setMenuOpen(false); }}
            className={`w-full px-4 py-2 rounded-lg text-left ${
              currentView === 'chat' ? 'bg-indigo-600 text-white' : 'text-gray-600'
            }`}
          >
            Chat Translator
          </button>
          <button
            onClick={() => { setCurrentView('history'); setMenuOpen(false); }}
            className={`w-full px-4 py-2 rounded-lg text-left flex items-center space-x-2 ${
              currentView === 'history' ? 'bg-indigo-600 text-white' : 'text-gray-600'
            }`}
          >
            <History className="w-4 h-4" />
            <span>History</span>
          </button>
          <button
            onClick={() => { setCurrentView('account'); setMenuOpen(false); }}
            className={`w-full px-4 py-2 rounded-lg text-left flex items-center space-x-2 ${
              currentView === 'account' ? 'bg-indigo-600 text-white' : 'text-gray-600'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Account</span>
          </button>
          <button
            onClick={() => { handleLogout(); setMenuOpen(false); }}
            className="w-full px-4 py-2 rounded-lg text-left text-red-600 hover:bg-red-50 flex items-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {currentView === 'text' && (
          <div className="h-full overflow-y-auto max-w-6xl mx-auto p-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center space-x-2">
                <Type className="w-6 h-6 text-indigo-600" />
                <span>Text Translator</span>
              </h2>

              {/* Language Selector */}
              <div className="flex flex-wrap gap-4 items-center justify-center mb-6">
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">From:</label>
                  <select
                    value={sourceLang}
                    onChange={(e) => handleSourceLangChange(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {languages.map(lang => (
                      <option key={lang.code} value={lang.code}>{lang.name}</option>
                    ))}
                  </select>
                </div>
                
                <button
                  onClick={swapLanguages}
                  className="p-2 hover:bg-gray-100 rounded-lg transition"
                  title="Swap languages"
                >
                  <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                </button>
                
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">To:</label>
                  <select
                    value={targetLang}
                    onChange={(e) => handleTargetLangChange(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {languages.map(lang => (
                      <option key={lang.code} value={lang.code}>{lang.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Text Areas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Enter text ({languages.find(l => l.code === sourceLang)?.name})
                  </label>
                  <textarea
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Type or paste text here..."
                    className="w-full h-64 border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                    disabled={isTranslating}
                  />
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-gray-500">{textInput.length} characters</span>
                    <button
                      onClick={() => setTextInput('')}
                      className="text-sm text-red-500 hover:text-red-700"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Translation ({languages.find(l => l.code === targetLang)?.name})
                  </label>
                  <div className="relative">
                    <textarea
                      value={textOutput}
                      readOnly
                      placeholder="Translation will appear here..."
                      className="w-full h-64 border border-gray-300 rounded-lg px-4 py-3 bg-gray-50 resize-none"
                    />
                    {textOutput && (
                      <button
                        onClick={copyToClipboard}
                        className="absolute top-3 right-3 p-2 bg-white rounded-lg hover:bg-gray-100 transition shadow-sm"
                        title="Copy to clipboard"
                      >
                        {copied ? (
                          <Check className="w-5 h-5 text-green-500" />
                        ) : (
                          <Copy className="w-5 h-5 text-gray-600" />
                        )}
                      </button>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-gray-500">{textOutput.length} characters</span>
                    {copied && <span className="text-sm text-green-500">Copied!</span>}
                  </div>
                </div>
              </div>

              {/* Translate Button */}
              <button
                onClick={handleTextTranslate}
                disabled={isTranslating || !textInput.trim()}
                className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center space-x-2"
              >
                {isTranslating ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Translating...</span>
                  </>
                ) : (
                  <>
                    <Globe className="w-5 h-5" />
                    <span>Translate</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {currentView === 'voice' && (
          <div className="h-full overflow-y-auto max-w-4xl mx-auto p-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center space-x-2">
                <Mic className="w-6 h-6 text-indigo-600" />
                <span>Voice Translator</span>
              </h2>

              {/* Language Selector */}
              <div className="flex flex-wrap gap-4 items-center justify-center mb-6">
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">Speak in:</label>
                  <select
                    value={sourceLang}
                    onChange={(e) => handleSourceLangChange(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {languages.map(lang => (
                      <option key={lang.code} value={lang.code}>{lang.name}</option>
                    ))}
                  </select>
                </div>
                
                <div className="text-gray-400">→</div>
                
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">Translate to:</label>
                  <select
                    value={targetLang}
                    onChange={(e) => handleTargetLangChange(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {languages.map(lang => (
                      <option key={lang.code} value={lang.code}>{lang.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Mode Selection */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border-2 border-blue-200">
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center space-x-2">
                    <Mic className="w-5 h-5 text-blue-600" />
                    <span>Speech to Speech</span>
                  </h3>
                  <p className="text-sm text-gray-600">Speak and hear translation</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border-2 border-green-200">
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center space-x-2">
                    <Mic className="w-5 h-5 text-green-600" />
                    <Type className="w-5 h-5 text-green-600" />
                  </h3>
                  <p className="text-sm text-gray-600">Speech to Text translation</p>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border-2 border-purple-200">
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center space-x-2">
                    <Type className="w-5 h-5 text-purple-600" />
                    <Volume2 className="w-5 h-5 text-purple-600" />
                  </h3>
                  <p className="text-sm text-gray-600">Text to Speech translation</p>
                </div>
              </div>

              {/* Recording Interface */}
              <div className="text-center mb-6">
                <div className={`inline-flex items-center justify-center w-32 h-32 rounded-full mb-4 transition-all ${
                  isRecording ? 'bg-red-500 animate-pulse' : 'bg-indigo-600 hover:bg-indigo-700'
                }`}>
                  {isRecording ? (
                    <button onClick={stopRecording} className="text-white">
                      <StopCircle className="w-16 h-16" />
                    </button>
                  ) : (
                    <button onClick={startRecording} className="text-white" disabled={isTranslating}>
                      <Mic className="w-16 h-16" />
                    </button>
                  )}
                </div>
                <p className="text-gray-600 font-medium">
                  {isRecording ? 'Recording... Click to stop' : 'Click microphone to start speaking'}
                </p>
                {isTranslating && (
                  <p className="text-indigo-600 mt-2">Translating...</p>
                )}
              </div>

              {/* Transcription and Translation Display */}
              {(audioTranscript || audioTranslation) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-800">
                        Original ({languages.find(l => l.code === sourceLang)?.name})
                      </h3>
                      {audioTranscript && (
                        <button
                          onClick={() => speakText(audioTranscript, sourceLang)}
                          disabled={isSpeaking}
                          className="text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
                          title="Listen"
                        >
                          <Volume2 className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                    <p className="text-gray-800 min-h-20">{audioTranscript}</p>
                  </div>

                  <div className="bg-indigo-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-800">
                        Translation ({languages.find(l => l.code === targetLang)?.name})
                      </h3>
                      <div className="flex space-x-2">
                        {audioTranslation && (
                          <>
                            <button
                              onClick={() => speakText(audioTranslation, targetLang)}
                              disabled={isSpeaking}
                              className="text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
                              title="Listen"
                            >
                              <Volume2 className="w-5 h-5" />
                            </button>
                            {isSpeaking && (
                              <button
                                onClick={stopSpeaking}
                                className="text-red-600 hover:text-red-700"
                                title="Stop"
                              >
                                <StopCircle className="w-5 h-5" />
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                    <p className="text-gray-800 min-h-20">{audioTranslation}</p>
                  </div>
                </div>
              )}

              {/* Clear Button */}
              {(audioTranscript || audioTranslation) && (
                <button
                  onClick={() => {
                    setAudioTranscript('');
                    setAudioTranslation('');
                    stopSpeaking();
                  }}
                  className="w-full mt-4 text-red-500 hover:text-red-700 py-2 rounded-lg hover:bg-red-50 transition"
                >
                  Clear All
                </button>
              )}

              {/* Browser Support Note */}
              <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> Voice features work best in Chrome, Edge, or Safari browsers. 
                  Make sure to allow microphone access when prompted.
                </p>
              </div>
            </div>
          </div>
        )}

        {currentView === 'chat' && (
          <div className="h-full flex flex-col max-w-4xl mx-auto p-4">
            {/* Language Selector */}
            <div className="bg-white rounded-lg shadow-md p-4 mb-4 flex flex-wrap gap-4 items-center justify-between">
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">From:</label>
                <select
                  value={sourceLang}
                  onChange={(e) => handleSourceLangChange(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  {languages.map(lang => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              </div>
              
              <div className="text-gray-400">→</div>
              
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">To:</label>
                <select
                  value={targetLang}
                  onChange={(e) => handleTargetLangChange(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  {languages.map(lang => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              </div>

              {messages.length > 0 && (
                <button
                  onClick={clearChat}
                  className="ml-auto text-red-500 hover:text-red-700 text-sm flex items-center space-x-1"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Clear</span>
                </button>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 bg-white rounded-lg shadow-md overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-gray-400">
                  <div className="text-center">
                    <Globe className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Start translating...</p>
                    <p className="text-sm mt-2">Type a message below to begin</p>
                  </div>
                </div>
              ) : (
                messages.map(msg => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xs md:max-w-md px-4 py-3 rounded-2xl ${
                        msg.type === 'user'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p className="text-sm mb-1">{msg.text}</p>
                      <p className="text-xs opacity-70 flex items-center justify-between">
                        <span>{languages.find(l => l.code === msg.lang)?.name}</span>
                        <span>{msg.timestamp}</span>
                      </p>
                    </div>
                  </div>
                ))
              )}
              {isTranslating && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 px-4 py-3 rounded-2xl">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="mt-4 flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type your message..."
                className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                disabled={isTranslating}
              />
              <button
                onClick={handleSend}
                disabled={isTranslating || !input.trim()}
                className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {currentView === 'history' && (
          <div className="h-full overflow-y-auto max-w-4xl mx-auto p-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Translation History</h2>
                <div className="flex space-x-2">
                  {history.length > 0 && (
                    <>
                      <button
                        onClick={downloadHistory}
                        className="text-indigo-600 hover:text-indigo-700 flex items-center space-x-1"
                      >
                        <Download className="w-4 h-4" />
                        <span>Export</span>
                      </button>
                      <button
                        onClick={clearHistory}
                        className="text-red-500 hover:text-red-700 flex items-center space-x-1"
                      >
                        <Trash2 className="w-4 h-4" />
                        <span>Clear</span>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {history.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <History className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No translation history yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {history.map(item => (
                    <div key={item.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-500">
                          {languages.find(l => l.code === item.from)?.name} → {languages.find(l => l.code === item.to)?.name}
                        </span>
                        <span className="text-xs text-gray-400">{item.date} {item.time}</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs font-semibold text-gray-600 mb-1">Original</p>
                          <p className="text-gray-800">{item.original}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-600 mb-1">Translation</p>
                          <p className="text-gray-800">{item.translated}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {currentView === 'account' && (
          <div className="h-full overflow-y-auto max-w-2xl mx-auto p-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Account Settings</h2>
              
              <div className="flex items-center space-x-4 mb-8">
                <div className="w-20 h-20 bg-indigo-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                  {userName.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-800">{userName}</h3>
                  <p className="text-gray-500">{userEmail}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                  <input
                    type="text"
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                  <input
                    type="email"
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div className="pt-4">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center space-x-2">
                    <Settings className="w-5 h-5" />
                    <span>Statistics</span>
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-indigo-50 rounded-lg p-4">
                      <p className="text-sm text-gray-600">Total Translations</p>
                      <p className="text-2xl font-bold text-indigo-600">{history.length}</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4">
                      <p className="text-sm text-gray-600">Active Chats</p>
                      <p className="text-2xl font-bold text-green-600">{messages.length}</p>
                    </div>
                  </div>
                </div>

                <button className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition mt-6">
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default LanguageTranslator;