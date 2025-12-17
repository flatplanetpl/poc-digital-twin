"""Data loaders for various file formats."""

from .base import BaseLoader
from .email_loader import EmailLoader
from .messenger_loader import MessengerLoader
from .text_loader import TextLoader
from .whatsapp_loader import WhatsAppLoader

# Facebook/Messenger data loaders
from .profile_loader import ProfileLoader
from .contacts_loader import ContactsLoader
from .location_loader import LocationLoader
from .search_history_loader import SearchHistoryLoader
from .ads_interests_loader import AdsInterestsLoader

__all__ = [
    # Base
    "BaseLoader",
    # Original loaders
    "TextLoader",
    "EmailLoader",
    "WhatsAppLoader",
    "MessengerLoader",
    # Facebook/Messenger data loaders
    "ProfileLoader",
    "ContactsLoader",
    "LocationLoader",
    "SearchHistoryLoader",
    "AdsInterestsLoader",
]
