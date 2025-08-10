"""
Discord Bot for WhatDoTheyKnow FOI Search and Flask Uptime Monitoring
"""

import os
import asyncio
import threading
import logging
import re
from urllib.parse import quote
import discord
from discord.ext import commands
from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app for uptime monitoring
app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint for uptime monitoring"""
    return jsonify({
        'status': 'online',
        'message': 'Discord bot is running'
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return jsonify({
        'status': 'healthy',
        'bot_status': 'connected' if bot.is_ready() else 'disconnected',
        'uptime': 'running'
    })

# Discord bot setup
intents = discord.Intents.default()
# Remove privileged intent requirement to work without developer portal configuration
intents.message_content = True  # This requires privileged intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Bot configuration - downloads and fetch functionality removed

def search_whatdotheyknow(query: str) -> tuple[bool, str, str, str, list]:
    """
    Search whatdotheyknow.com for the given query and return first result
    Returns: (success, title, url, snippet, pdf_links)
    """
    import time
    import random

    try:
        # Encode query for URL
        encoded_query = quote(query)
        search_url = f"https://www.whatdotheyknow.com/search/{encoded_query}"

        # Make request with proper headers and session for better reliability
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                    time.sleep(delay)

                with requests.Session() as session:
                    response = session.get(search_url, headers=headers, timeout=20)

                    if response.status_code == 503:
                        if attempt == max_retries - 1:
                            return False, "", "", "WhatDoTheyKnow.com is currently under heavy load or maintenance. Please try again in a few minutes."
                        continue  # Try again

                    if response.status_code == 429:  # Rate limited
                        if attempt == max_retries - 1:
                            return False, "", "", "Rate limited by WhatDoTheyKnow.com. Please wait a moment and try again."
                        continue  # Try again

                    response.raise_for_status()
                    break  # Success, exit retry loop

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1:
                    return False, "", "", f"Connection failed: {str(e)}"
                continue  # Try again

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Method 1: Look for FOI requests section
        foi_requests_section = soup.find('h2', string=lambda text: text and 'FOI requests' in text and 'of' in text)

        if foi_requests_section:
            # Find request links after this heading
            current = foi_requests_section.find_next()
            while current and not (current.name == 'a' and current.get('href', '').startswith('/request/')):
                current = current.find_next()

            if current:
                title = current.get_text(strip=True)
                relative_url = current.get('href')
                full_url = f"https://www.whatdotheyknow.com{relative_url}"

                # Extract snippet from the surrounding context
                snippet_text = ""
                parent = current.find_parent()
                if parent:
                    snippet_text = parent.get_text(strip=True)
                    # Clean up the snippet
                    if len(snippet_text) > 300:
                        snippet_text = snippet_text[:300] + "..."

                # Look for PDF links in the search result page
                pdf_links = find_pdf_links_on_page(full_url)
                return True, title, full_url, snippet_text or "No description available", pdf_links

        # Method 2: Fallback - look for any request links
        request_links = soup.find_all('a', href=lambda href: href and '/request/' in href and not href.startswith('javascript'))

        if request_links:
            first_link = request_links[0]
            title = first_link.get_text(strip=True)
            relative_url = first_link.get('href')
            full_url = f"https://www.whatdotheyknow.com{relative_url}"

            # Get context from the link's container
            container = first_link.find_parent(['div', 'article', 'section', 'p'])
            snippet = ""
            if container:
                snippet = container.get_text(strip=True)[:300] + "..."

            # Look for PDF links in the search result page
            pdf_links = find_pdf_links_on_page(full_url)
            return True, title, full_url, snippet or "FOI request found", pdf_links

        # Method 3: Check if we have any content at all
        if soup.find('title'):
            page_title = soup.find('title').get_text(strip=True)
            if "search" in page_title.lower():
                return False, "", "", f"Search completed but no results found for '{query}'. Try different keywords.", []

        return False, "", "", "No search results found or page could not be parsed", []

    except requests.exceptions.Timeout:
        return False, "", "", "Search request timed out", []
    except requests.exceptions.RequestException as e:
        return False, "", "", f"Search request failed: {str(e)}", []
    except Exception as e:
        return False, "", "", f"Search error: {str(e)}", []

def find_pdf_links_on_page(url: str) -> list[dict]:
    """
    Find PDF links on a WhatDoTheyKnow request page
    Returns list of dictionaries with pdf info: [{'name': str, 'url': str, 'size': str}]
    """
    import time
    import random

    try:
        time.sleep(random.uniform(0.5, 1.0))  # Small delay to be respectful

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            pdf_links = []

            # Method 1: Look for attachment sections with PDF files
            attachment_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'attachment' in x.lower())
            if not attachment_sections:
                # Look for any sections containing "Attachments" text
                for element in soup.find_all(text=lambda text: text and 'attachment' in text.lower()):
                    parent = element.find_parent()
                    if parent:
                        attachment_sections.append(parent)

            # Method 2: Look for direct PDF download links
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link.get('href', '')
                if not href:
                    continue

                # Get link text for analysis
                link_text = link.get_text(strip=True)

                # Check multiple patterns for PDF detection
                is_pdf = False
                pdf_name = ""
                size_info = "Size unknown"

                # Pattern 1: Direct .pdf URLs
                if href.lower().endswith('.pdf'):
                    is_pdf = True
                    pdf_name = href.split('/')[-1].split('?')[0]

                # Pattern 2: WhatDoTheyKnow attachment URLs (exclude HTML versions)
                elif ('/response/' in href and '/attach/' in href and '.pdf' in href and 
                      '/attach/html/' not in href):
                    is_pdf = True
                    # Extract PDF name from URL - format: /attach/2/filename.pdf
                    url_parts = href.split('/')
                    for i, part in enumerate(url_parts):
                        if part == 'attach' and i + 2 < len(url_parts):
                            pdf_name = url_parts[i + 2].split('?')[0]
                            # Decode URL encoding
                            import urllib.parse
                            pdf_name = urllib.parse.unquote(pdf_name)
                            break

                # Pattern 3: Links with "Download" text and PDF in context (but not HTML versions)
                elif (('download' in link_text.lower()) and 
                      '.pdf' in href and '.html' not in href):
                    is_pdf = True
                    # Extract name from surrounding context
                    container = link.find_parent(['li', 'div', 'p', 'td'])
                    if container:
                        container_text = container.get_text(strip=True)
                        # Look for .pdf filename in the container
                        import re
                        pdf_match = re.search(r'([^\s]+\.pdf)', container_text, re.IGNORECASE)
                        if pdf_match:
                            pdf_name = pdf_match.group(1)

                if is_pdf:
                    # Make absolute URL if needed
                    if href.startswith('/'):
                        full_pdf_url = f"https://www.whatdotheyknow.com{href}"
                    elif not href.startswith('http'):
                        full_pdf_url = f"https://www.whatdotheyknow.com/{href}"
                    else:
                        full_pdf_url = href

                    # Clean up PDF name
                    if not pdf_name:
                        pdf_name = link_text if link_text and '.pdf' in link_text.lower() else "document.pdf"

                    # Look for size information in surrounding elements
                    container = link.find_parent(['li', 'div', 'section', 'article'])
                    if container:
                        container_text = container.get_text()
                        # Look for size patterns like "175K", "9.5M", "1.2MB", etc.
                        import re
                        size_patterns = [
                            r'(\d+(?:\.\d+)?)\s*(KB|MB|GB|K|M|G)\b',
                            r'(\d+(?:\.\d+)?)(K|M|G)\b'
                        ]
                        for pattern in size_patterns:
                            size_match = re.search(pattern, container_text, re.IGNORECASE)
                            if size_match:
                                size_num = size_match.group(1)
                                size_unit = size_match.group(2).upper()
                                # Normalize units
                                if size_unit in ['K', 'KB']:
                                    size_unit = 'KB'
                                elif size_unit in ['M', 'MB']:
                                    size_unit = 'MB'
                                elif size_unit in ['G', 'GB']:
                                    size_unit = 'GB'
                                size_info = f"{size_num} {size_unit}"
                                break

                    pdf_info = {
                        'name': pdf_name[:100],  # Limit name length
                        'url': full_pdf_url,
                        'size': size_info
                    }

                    # Avoid duplicates by checking both name and URL
                    duplicate = False
                    for existing_pdf in pdf_links:
                        if (existing_pdf['name'] == pdf_info['name'] or 
                            existing_pdf['url'] == pdf_info['url']):
                            duplicate = True
                            break

                    if not duplicate:
                        pdf_links.append(pdf_info)

            return pdf_links[:5]  # Limit to 5 PDFs max

    except Exception as e:
        logger.error(f"Error finding PDFs on {url}: {e}")
        return []

@bot.event
async def on_ready():
    """Event triggered when bot successfully connects to Discord"""
    print(f"✅ Logged in as {bot.user}")
    logger.info(f"Bot logged in as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for bot commands"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands

    logger.error(f"Command error: {error}")
    await ctx.send(f"❌ An error occurred: {str(error)}")

# Download and fetch functionality removed per user request

@bot.command(name='search')
async def search_command(ctx, *, query: str = None):
    """
    Search whatdotheyknow.com for FOI requests
    Usage: !search <keywords>
    """
    if not query:
        await ctx.send("❌ Please provide search keywords. Usage: `!search <keywords>`")
        return

    # Send initial response
    message = await ctx.send(f"🔍 Searching whatdotheyknow.com for: **{query}**")

    try:
        # Perform search
        success, title, url, snippet, pdf_links = search_whatdotheyknow(query)

        if success:
            # Create formatted response
            embed = discord.Embed(
                title=title[:256],  # Discord embed title limit
                url=url,
                description=snippet[:4096],  # Discord embed description limit
                color=0x3498db  # Blue color
            )
            embed.set_footer(text="Source: WhatDoTheyKnow.com")
            embed.add_field(name="🔗 Link", value=f"[View full request]({url})", inline=False)

            # Add PDF information if found
            if pdf_links:
                pdf_text = "\n".join([f"📄 **{pdf['name']}** ({pdf['size']})" for pdf in pdf_links[:3]])
                embed.add_field(name="📋 Available PDFs", value=pdf_text, inline=False)

                # Display direct download links (truncate long filenames)
                pdf_links_text = "\n".join([f"[📥 {pdf['name'][:40]}...]({pdf['url']})" if len(pdf['name']) > 40 else f"[📥 {pdf['name']}]({pdf['url']})" for pdf in pdf_links[:3]])
                if len(pdf_links_text) > 1000:  # Ensure field stays under Discord's 1024 character limit
                    pdf_links_text = pdf_links_text[:950] + "..."
                embed.add_field(name="🔗 Direct Download Links", value=pdf_links_text, inline=False)

                if len(pdf_links) > 10:
                    embed.add_field(name="ℹ️ Note", value=f"Showing first 3 of {len(pdf_links)} PDFs found, there may be more!", inline=False)

            # Simply edit the original message to show results with direct download links
            await message.edit(content=f"✅ **Search Results for:** {query}", embed=embed)

            logger.info(f"Search completed for query: {query} - Found {len(pdf_links)} PDFs")

        else:
            await message.edit(content=f"❌ Search failed: {snippet}")
            logger.error(f"Search failed for {query}: {snippet}")

    except Exception as e:
        await message.edit(content=f"❌ Unexpected error during search: {str(e)}")
        logger.error(f"Unexpected error during search: {e}")

@bot.command(name='help_bot')
async def help_command(ctx):
    """Show available bot commands"""
    help_text = """
🤖 **Discord Search Bot for WhatDoTheyKnow**

**Available Commands:**
• `!search <keywords>` - Search whatdotheyknow.com for FOI requests
• `!help_bot` - Show this help message

**Features:**
• Search UK Freedom of Information requests
• Find PDF documents in FOI responses
• Get direct download links to documents
• Error handling and validation

**Examples:**
• `!search police corruption`
• `!search cambridge trinity a100 interview scores`
• `!search government contracts covid`

    """
    await ctx.send(help_text)

def run_flask_server():
    """Run Flask server for uptime monitoring"""
    try:
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

async def main():
    """Main function to run both Discord bot and Flask server"""
    # Validate environment variable
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ DISCORD_BOT_TOKEN environment variable is not set!")
        print("❌ Error: DISCORD_BOT_TOKEN environment variable is required!")
        return

    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("🌐 Flask uptime monitoring server started on port 8080")

    try:
        # Start Discord bot
        await bot.start(bot_token)
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord bot token!")
        print("❌ Error: Invalid Discord bot token!")
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        print(f"❌ Critical error: {e}")
