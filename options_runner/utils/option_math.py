from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks
from options_runner.config import RISK_FREE_RATE

def calculate_greeks(df, current_price, option_type='c', model='black_scholes'):
    """
    Calculates IV and Greeks for a DataFrame of options.
    
    Args:
        df: DataFrame with 'mid', 'strike', 'time_to_expiry' columns.
        current_price: Underlying price.
        option_type: 'c' for call, 'p' for put.
        model: Pricing model.
        
    Returns:
        DataFrame with added columns: 'iv', 'delta', 'theta', 'vega', 'gamma', 'rho'
    """
    # Calculate IV
    df['iv'] = vectorized_implied_volatility(
        df['mid'], 
        current_price, 
        df['strike'], 
        df['time_to_expiry'], 
        RISK_FREE_RATE, 
        option_type, 
        q=0, 
        return_as='numpy'
    )
    
    # Calculate Greeks
    greeks = get_all_greeks(
        option_type, 
        current_price, 
        df['strike'], 
        df['time_to_expiry'], 
        RISK_FREE_RATE, 
        df['iv'], 
        q=0, 
        model=model, 
        return_as='dict'
    )
    
    df['delta'] = greeks['delta']
    df['theta'] = greeks['theta']
    df['vega'] = greeks['vega']
    df['gamma'] = greeks['gamma']
    df['rho'] = greeks['rho']
    
    return df
