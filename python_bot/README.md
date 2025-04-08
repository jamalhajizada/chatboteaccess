# Microsoft Teams Bot (Python)

A simple Microsoft Teams bot implemented in Python that responds with "hello!" to any message.

## Setup Instructions

1. Create a Python virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   ```
   # On Windows
   venv\Scripts\activate
   ```

3. Install required packages:
   ```
   pip install -r requirements.txt
   ```

4. Update the `.env` file with your Bot credentials:
   ```
   MicrosoftAppId=your-app-id
   MicrosoftAppPassword=your-app-password
   PORT=3978
   ```

5. Start the bot:
   ```
   python app.py
   ```

## Testing Your Bot

To test locally, you can use the [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator/releases/latest)

## Deploying to Microsoft Teams

1. Deploy this bot to a server (could be Azure App Service or your company's server)
2. Make sure the server endpoint is accessible from the internet
3. In Azure Bot Service, configure your messaging endpoint to point to `https://your-server-url/api/messages`
4. Add the Microsoft Teams channel in Azure Bot Service
5. Install the bot in your Microsoft Teams tenant

## Project Structure

- `app.py` - Main entry point that sets up the web server and adapters
- `bot.py` - Bot implementation that responds to messages with "hello!"
- `.env` - Configuration settings for the bot
