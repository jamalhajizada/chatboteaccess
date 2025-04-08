import os
import msal
import requests
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('graph_helper')

# Load environment variables
load_dotenv()

# Graph API configuration
CLIENT_ID = os.getenv("MicrosoftAppId", "")
CLIENT_SECRET = os.getenv("MicrosoftAppPassword", "")
TENANT_ID = os.getenv("MicrosoftAppTenantId", "")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

def get_access_token():
    """
    Get an access token for Microsoft Graph API using client credentials flow.
    """
    if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
        logger.error("Missing Microsoft app credentials in environment variables")
        return None
        
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    
    # Acquire token for Microsoft Graph
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        logger.info("Successfully acquired access token")
        return result["access_token"]
    else:
        logger.error(f"Error getting token: {result.get('error')} - {result.get('error_description')}")
        return None

def get_user_by_email_or_upn(email_or_upn):
    """
    Look up a user in Azure AD by email or UPN.
    """
    if not email_or_upn:
        return None
        
    token = get_access_token()
    if not token:
        return None
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Query for users with matching email or UPN
        filter_query = f"userPrincipalName eq '{email_or_upn}' or mail eq '{email_or_upn}'"
        response = requests.get(
            f"{GRAPH_ENDPOINT}/users?$filter={filter_query}&$select=id,displayName,userPrincipalName,mail",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("value") and len(data["value"]) > 0:
                logger.info(f"Found user by email/upn: {email_or_upn}")
                return data["value"][0]
        
        logger.info(f"No user found with email/upn: {email_or_upn}")
        return None
    except Exception as e:
        logger.error(f"Error looking up user by email/upn: {str(e)}")
        return None

def get_user_by_display_name(display_name):
    """
    Look up a user in Azure AD by display name.
    """
    if not display_name:
        return None
        
    token = get_access_token()
    if not token:
        return None
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Query for users with matching display name
        response = requests.get(
            f"{GRAPH_ENDPOINT}/users?$filter=displayName eq '{display_name}'&$select=id,displayName,userPrincipalName,mail",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("value") and len(data["value"]) > 0:
                logger.info(f"Found user by display name: {display_name}")
                return data["value"][0]
        
        logger.info(f"No user found with display name: {display_name}")
        return None
    except Exception as e:
        logger.error(f"Error looking up user by display name: {str(e)}")
        return None

def get_ad_account_for_teams_user(activity):
    """
    Extract AD account information for a Teams user from their activity.
    Returns a dictionary with UPN, email, and display name if found.
    
    This function uses only one reliable method: looking up by display name.
    """
    if not hasattr(activity, 'from_property') or not activity.from_property:
        logger.warning("Activity missing from_property")
        return None
    
    teams_id = activity.from_property.id
    display_name = activity.from_property.name if hasattr(activity.from_property, 'name') else None
    
    logger.info(f"Looking up Teams user: ID={teams_id}, Name={display_name}")
    
    # Get tenant ID from the activity if available
    tenant_id = None
    if (hasattr(activity, 'channel_data') and activity.channel_data and 
        isinstance(activity.channel_data, dict) and 'tenant' in activity.channel_data and 
        'id' in activity.channel_data['tenant']):
        tenant_id = activity.channel_data['tenant']['id']
        logger.info(f"Found tenant ID: {tenant_id}")
    
    # Prepare result with Teams info
    result = {
        "teams_id": teams_id,
        "teams_display_name": display_name,
        "tenant_id": tenant_id
    }
    
    # Try finding by display name if available
    user_info = None
    if display_name:
        logger.info(f"Looking up user by display name: {display_name}")
        user_info = get_user_by_display_name(display_name)
        
        if user_info:
            result.update({
                "ad_display_name": user_info.get("displayName"),
                "upn": user_info.get("userPrincipalName"),
                "email": user_info.get("mail"),
                "ad_object_id": user_info.get("id")
            })
            logger.info(f"Successfully found AD account: {result.get('upn')}")
        else:
            logger.info(f"Could not find AD account for Teams user with display name: {display_name}")
    else:
        logger.warning("No display name available for Teams user")
    
    return result
