taskflow-discord-bot/
│
├── bot.py                         # Main bot launcher - stateless Discord bot
├── .env                           # Secrets: bot token, backend API URL
├── requirements.txt               # Python dependencies
│
├── commands/                      # All slash command definitions
│   ├── __init__.py
│   ├── basic.py                   # /ping, /help
│   └── auth.py                    # /link command - passes user ID to backend
│
├── services/                      # Backend API communication layer
│   ├── __init__.py
│   └── api_client.py              # HTTP client for backend API calls
│
├── utils/                         # Supporting tools
│   ├── __init__.py
│   ├── error_handler.py           # Central error handling logic
│   └── auth_headers.py            # User identity header management
│
└── README.md                      # Setup guide, contributor instructions

## Architecture Overview

### Stateless Bot Design
- Bot maintains no user state or database connections
- All user data and authorization handled by backend API
- User identity passed via headers in API requests
- Backend resolves user permissions and handles business logic

### API Communication
- Bot sends user ID and context via headers to backend
- Backend handles user resolution, authorization, and data persistence
- Bot simply relays responses back to Discord

### Security
- User identity passed securely via headers
- Backend validates Discord user tokens/identity
- No sensitive data stored in bot

