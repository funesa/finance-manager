"""
Utility functions for currency formatting, date manipulation, and common UI helpers.
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
import locale

def setup_locale():
    """Sets the locale to Portuguese (Brazil) for date and currency formatting."""
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '')

def format_currency(value: float) -> str:
    """Formats a float as BRL currency string."""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def get_month_range(month_str: str = None):
    """
    Returns navigation data for a given month string (YYYY-MM).
    If no month_str is provided, uses the current month.
    """
    if month_str:
        try:
            target_date = datetime.strptime(month_str, '%Y-%m')
        except ValueError:
            target_date = datetime.now()
    else:
        target_date = datetime.now()

    target_month_str = target_date.strftime('%Y-%m')
    
    # We use a trick to get localized month name without global locale side effects if possible
    # but for simplicity in this project we rely on the setup_locale() call.
    target_month_display = target_date.strftime('%b/%Y').capitalize()
    
    prev_month = (target_date - relativedelta(months=1)).strftime('%Y-%m')
    next_month = (target_date + relativedelta(months=1)).strftime('%Y-%m')
    next_month_display = (target_date + relativedelta(months=1)).strftime('%b/%Y').capitalize()

    return {
        'target_date': target_date,
        'month_str': target_month_str,
        'display': target_month_display,
        'prev_month': prev_month,
        'next_month': next_month,
        'next_month_display': next_month_display
    }

def parse_amount(amount_str: str) -> float:
    """Parses a string amount (possibly with comma) into a float."""
    if not amount_str:
        return 0.0
    try:
        return float(amount_str.replace('.', '').replace(',', '.'))
    except (ValueError, AttributeError):
        try:
            return float(amount_str.replace(',', '.'))
        except ValueError:
            return 0.0
