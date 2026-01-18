"""Services package for AI Content Telegram Bot."""

# Import image_fetcher separately as it has no external dependencies
from .image_fetcher import ImageFetcher

# These imports require SQLAlchemy and other dependencies
try:
    from .user_service import add_user, get_user, activate_subscription, is_premium, count_premium
    from .payment_service import create_invoice, handle_pre_checkout, handle_success
    
    __all__ = [
        'add_user',
        'get_user', 
        'activate_subscription',
        'is_premium',
        'count_premium',
        'create_invoice',
        'handle_pre_checkout',
        'handle_success',
        'ImageFetcher'
    ]
except ImportError:
    # If dependencies are not available, only export ImageFetcher
    __all__ = ['ImageFetcher']
