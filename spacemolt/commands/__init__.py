import math


def paginate(items, limit=10, page=1):
    """Slice a list for pagination. Returns (page_items, total, total_pages, page)."""
    limit = max(1, limit)
    page = max(1, page)
    total = len(items)
    total_pages = max(1, math.ceil(total / limit))
    page = min(page, total_pages)
    start = (page - 1) * limit
    return items[start:start + limit], total, total_pages, page


def print_page_footer(total, total_pages, page, limit):
    """Print a standard pagination footer if there are multiple pages."""
    if total_pages > 1:
        print(f"\nPage {page}/{total_pages} ({total} total)  --  --page {page + 1} for next")


from spacemolt.commands.passthrough import *
from spacemolt.commands.info import *
from spacemolt.commands.actions import *
from spacemolt.commands.missions import *
from spacemolt.commands.insurance import *
from spacemolt.commands.storage import *
from spacemolt.commands.market import *
from spacemolt.commands.facility import *
