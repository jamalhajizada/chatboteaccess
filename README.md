# MS Teams Bot with EA Access & Langflow Integration

An intelligent Microsoft Teams bot that integrates with Langflow for AI-powered conversations and provides an interactive asset selection interface for EA (Enterprise Architecture) access management.

## Features

- 🤖 **AI-Powered Conversations**: Integrates with Langflow for intelligent responses
- 📋 **Interactive Asset Selection**: Multi-select dropdown with search functionality using Adaptive Cards
- 🔍 **Smart Search**: Filter through assets easily with the built-in search box
- 🎯 **Context-Aware**: Maintains conversation context and handles user selections
- 🛡️ **Error Handling**: Graceful error handling with user-friendly messages
- 🔐 **Secure**: Environment-based configuration for sensitive credentials

## Architecture

The bot uses:
- **Python 3.11+** with Bot Framework SDK
- **Langflow** for AI conversation management
- **Adaptive Cards** for rich interactive UI
- **Microsoft Graph API** for Teams integration

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Microsoft Azure account
- Langflow instance running and accessible
- Microsoft Teams admin access

### 1. Register Bot with Microsoft Bot Service

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new "Azure Bot" resource
3. Note the **Microsoft App ID** and generate a **Client Secret**
4. Add the Microsoft Teams channel to your bot

### 2. Configure Environment Variables

Create a `.env` file in the `python_bot` directory:

```env
MicrosoftAppId=your-app-id-here
MicrosoftAppPassword=your-app-password-here
MicrosoftAppType=MultiTenant
MicrosoftAppTenantId=your-tenant-id-here
PORT=3978
LANGFLOW_URL=http://your-langflow-instance:7860/api/v1/run/your-flow-id
```

### 3. Install Dependencies

```bash
cd python_bot
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Linux/Mac

pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python app.py
```

The bot will start on `http://localhost:3978`

### 5. Test Locally (Optional)

Use the [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator/releases/latest) to test locally:
1. Download and install the emulator
2. Connect to `http://localhost:3978/api/messages`
3. Enter your Microsoft App ID and Password

### 6. Deploy to Production

For production deployment:
1. Deploy to Azure App Service, AWS, or your preferred hosting platform
2. Update the bot's messaging endpoint in Azure Portal
3. Ensure the Langflow instance is accessible from your deployment

## Project Structure

```
bot-eaacess/
├── python_bot/
│   ├── app.py              # Flask application entry point
│   ├── bot.py              # Main bot logic and message handling
│   ├── graph_helper.py     # Microsoft Graph API helper
│   ├── assets_list.py      # Asset data management
│   ├── .env                # Environment configuration (not in repo)
│   └── requirements.txt    # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Key Features Explained

### Asset Selection Interface

When the bot receives a `SHOW_ASSET_DROPDOWN` keyword from Langflow, it displays an interactive Adaptive Card with:
- Searchable dropdown with all available assets
- Multi-select capability using checkboxes
- User-friendly interface with clear instructions

### Langflow Integration

The bot forwards all user messages to Langflow and processes the responses:
- Regular text responses are displayed directly
- Special keywords trigger interactive UI elements
- Selected assets are sent back to Langflow for processing

### Error Handling

Robust error handling for:
- Langflow connection issues
- Timeout scenarios
- Invalid responses
- Network errors

## Usage

1. **Start a conversation**: Send any message to the bot
2. **Request asset access**: The bot will guide you through the process
3. **Select assets**: Use the interactive dropdown to search and select multiple assets
4. **Submit**: Your selections are processed by the AI backend

## Development

### Adding New Assets

Edit `assets_list.py` to add or modify the asset list:

```python
ASSETS = [
    "Asset Name 1",
    "Asset Name 2",
    # Add more assets here
]
```

### Customizing Adaptive Cards

Modify the card structure in `bot.py` in the `create_asset_selection_card()` method.

### Extending Langflow Integration

Update the `send_to_langflow()` method in `bot.py` to customize the API integration.

## Troubleshooting

### Bot not responding
- Check if the bot service is running
- Verify environment variables are set correctly
- Check Azure Bot Service messaging endpoint

### Langflow connection issues
- Ensure Langflow URL is correct and accessible
- Check network connectivity
- Verify API endpoint format

### Asset dropdown not showing
- Check bot logs for errors
- Verify Adaptive Cards are supported in your Teams client
- Ensure the card JSON structure is valid

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Contact the development team

## Acknowledgments

- Microsoft Bot Framework team
- Langflow community
- Adaptive Cards team
