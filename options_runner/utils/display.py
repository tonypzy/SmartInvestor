import pandas as pd
from options_runner.config import DISPLAY_WIDTH, DISPLAY_FLOAT_FORMAT

def setup_pandas_display():
    """Sets up global pandas display options for better CLI readability."""
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', DISPLAY_WIDTH)
    pd.set_option('display.float_format', DISPLAY_FLOAT_FORMAT)
