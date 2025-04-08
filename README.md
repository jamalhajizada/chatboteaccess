# Microsoft Teams Bot

A simple Microsoft Teams bot that responds with "hello!" to any message.

## Setup Instructions

1. Register a bot with Microsoft Bot Service:
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new "Bot Channels Registration"
   - After creation, note the Microsoft App ID and generate a password

2. Update the `.env` file with your Bot credentials:
   ```
   MicrosoftAppId=your-app-id
   MicrosoftAppPassword=your-app-password
   PORT=3978
   ```

3. Install dependencies:
   ```
   npm install
   ```

4. Start the bot:
   ```
   npm start
   ```

5. To test locally, you can use the [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator/releases/latest)

6. To add the bot to Microsoft Teams:
   - Go to your Azure Bot Channels Registration
   - Add the Microsoft Teams channel
   - Follow the instructions to install the bot to your Teams tenant
   
## Project Structure

- `index.js` - Main entry point that sets up the server and adapters
- `bot.js` - Bot implementation that responds to messages
- `.env` - Configuration settings for the bot
