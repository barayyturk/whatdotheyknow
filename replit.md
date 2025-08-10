# Overview

A Discord bot application with search capabilities for UK Freedom of Information requests, plus integrated Flask web server for uptime monitoring. The bot responds to Discord commands and searches the UK's WhatDoTheyKnow.com Freedom of Information database. The Flask server provides health check endpoints to monitor the bot's status and ensure continuous uptime.

# User Preferences

Preferred communication style: Simple, everyday language.

# Deployment Configuration

## Always-On Operation
- **Deployment Method**: Use Replit's Reserved VM Deployments for continuous operation
- **Key Benefits**: 
  - Runs 24/7 even when computer is off
  - Dedicated computing resources with predictable performance
  - Always-on cloud server for reliable Discord bot hosting
- **Setup Instructions**: Navigate to Deployments workspace tool, select "Reserved VM" option, then "Set up your deployment"
- **Important Notes**: 
  - Reserved VM Deployments provide persistent uptime (unlike Autoscale which scales to zero)
  - No persistent storage included - data saved to filesystem won't persist after redeployment
  - Configuration includes CPU/RAM options, custom domains, and private deployment settings

# System Architecture

## Bot Framework
- **Discord.py Library**: Uses the discord.py library with commands extension for structured command handling
- **Command Prefix**: Configured with '!' prefix for bot commands
- **Intents**: Default intents configuration (privileged intents disabled for compatibility)
- **Commands Available**: 
  - `!search <keywords>` - Search WhatDoTheyKnow.com FOI database with PDF detection
  - `!help_bot` - Show command help
- **Interactive Features**:
  - Direct PDF Links: When PDFs are found, bot displays clickable download links in search results
  - No Thread Creation: Simplified approach with all information in the main search result
  - Immediate Access: Users can click links to download PDFs directly from WhatDoTheyKnow.com
  - Clean Interface: All PDF information displayed in organized embed format

## Web Server Integration
- **Flask Application**: Integrated Flask web server running alongside the Discord bot
- **Health Monitoring**: Provides REST endpoints for uptime monitoring and status checks
- **Concurrent Execution**: Bot and web server run concurrently using threading

## Search & Web Integration
- **Web Search Integration**: Search functionality for WhatDoTheyKnow.com FOI database using requests and BeautifulSoup
- **Search Features**: URL encoding, HTML parsing, result extraction with title, URL, and snippet
- **Advanced PDF Detection**: Multi-pattern detection system that identifies PDF attachments from WhatDoTheyKnow.com pages using multiple methods:
  - Direct .pdf URL detection
  - WhatDoTheyKnow attachment URL parsing (/response/.../attach/...)
  - Context-aware PDF link identification with size extraction
  - HTML version filtering to ensure only downloadable PDFs are detected
- **Direct Link Access**: Provides clickable links to PDFs found in FOI requests for direct download from WhatDoTheyKnow.com
- **Smart Error Handling**: Robust error recovery with browser-like headers, retry logic with exponential backoff, and rate limiting prevention

## Monitoring & Logging
- **Structured Logging**: Comprehensive logging system with timestamps and log levels
- **Health Endpoints**: Multiple endpoints (/status, /) for different monitoring needs
- **Bot Status Tracking**: Real-time bot connection status reporting

## Architectural Patterns
- **Asynchronous Design**: Leverages async/await for non-blocking operations
- **Separation of Concerns**: Clear separation between Discord bot logic and web monitoring
- **Modular Structure**: Flask and Discord components are independently manageable

# External Dependencies

## Core Libraries
- **discord.py**: Discord API wrapper for bot functionality
- **Flask**: Lightweight web framework for HTTP endpoints
- **requests**: HTTP library for web scraping and API calls
- **beautifulsoup4**: HTML parsing library for extracting search results

## System Dependencies
- **asyncio**: Python's async framework for concurrent operations
- **threading**: Standard library for running Flask server alongside bot
- **logging**: Built-in logging for application monitoring
- **urllib.parse**: URL parsing and validation utilities

## Runtime Environment
- **Discord API**: Integration with Discord's REST and Gateway APIs
- **HTTP Client**: External file downloading from web URLs
- **File System**: Local file storage and directory management