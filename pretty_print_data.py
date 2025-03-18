import json
from typing import List, Dict, Any
import textwrap
from colorama import init, Fore, Style

def pretty_print_markets(markets_data: List[Dict[str, Any]]) -> None:
  """
  Pretty prints market_summary data with highlighted key information.
  
  Args:
      markets_data: List of market_summary dictionaries containing prediction data
  """
  # Initialize colorama for cross-platform colored terminal output
  init()
  
  # Print each market_summary group
  for idx, market_summary in enumerate(markets_data):
    # Print divider between markets
    if idx > 0:
      print("\n" + "="*80 + "\n")
    
    # Print title
    wrapped_title = textwrap.fill(market_summary['title'], width=80)
    print(f"{Fore.CYAN}{Style.BRIGHT}MARKET: {wrapped_title}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Condition ID: {market_summary['condition_id']}{Style.RESET_ALL}")
    print()
    # Define colors based on adjusted EV
    ev_color = Fore.GREEN if market_summary['adjusted_ev'] > 0 else Fore.RED
    edge_color = Fore.GREEN if market_summary['edge'] > 0 else Fore.RED
    
    # Determine a symbol based on EV
    symbol = "🟢" if market_summary['adjusted_ev'] > 0 else "🔴"
    
    # Print outcome with key stats
    print(f"{Fore.YELLOW}{Style.BRIGHT}Outcome: {market_summary['outcome']}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Probability: {market_summary['probability']:.2f} (Model Confidence: {market_summary['confidence_level'] if 'confidence_level' in market_summary else market_summary['model_confidence']:.2f}){Style.RESET_ALL}")
    print(f"  {edge_color}Edge: {market_summary['edge']:.3f}{Style.RESET_ALL}")
    print(f"  {ev_color}Adjusted EV: {market_summary['adjusted_ev']:.3f} {symbol}{Style.RESET_ALL}")
    print(f"  Best Ask: {market_summary['best_ask_price']} (Size: {market_summary['best_ask_size']})")
    
    # Print uncertainty range if available
    if 'uncertainty' in market_summary:
      unc = market_summary['uncertainty']
      print(f"  {Fore.MAGENTA}Uncertainty Range: [{unc['lower_bound']:.2f}-{unc['upper_bound']:.2f}] (CL: {unc['confidence_level']:.2f}){Style.RESET_ALL}")
    
    print()