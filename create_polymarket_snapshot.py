#!/usr/bin/env python3
import dotenv
import os
import pickle
import py_clob_client
import requests
import prediction_pipeline
from datetime import datetime, timedelta, timezone
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY

env = dotenv.dotenv_values(".env")
HOST = "https://clob.polymarket.com"
POLYMARKET_KEY = env["PK"]
CHAIN_ID = POLYGON

def fetch_all_events_from_gamma():
  """
  Fetch all events from Gamma API.
  """
  events = []
  offset = 0
  limit = 100  # Max results per page
  
  while True:
    url = "https://gamma-api.polymarket.com/events"
    params = {
      "closed": "false",
      "active": "true",
      "limit": limit,
      "offset": offset,
      "order": "createdAt",
      "ascending": "false"
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
      print(f"Error fetching events: {response.status_code}")
      break
        
    batch = response.json()
    if not batch:  # No more results
      break
        
    events.extend(batch)
    offset += limit
      
  return events

def fetch_all_markets(client):
  """
  Fetch all markets from CLOB, iterating through all possible pages.
  """
  markets = []
  next_cursor = ""

  while True:
    response = client.get_markets(next_cursor=next_cursor)
    if not response or 'data' not in response:
      break
    markets.extend(response['data'])

    next_cursor = response.get('next_cursor', '')
    if next_cursor == 'LTE=' or not next_cursor:
      break

  return markets

def fetch_all_active_orderbooks(client, markets):
  # Fetch and attach order books for each market
  # (We can do this unconditionally, or add a check if you want to separately pickle the order-book-fetched markets)
  order_books = {}
  for _, market in markets.items():
    if not market['active'] or market['closed']:
      continue

    tokens = market.get('tokens', [])
    for token in tokens:
      token_id = token.get('token_id', None)
      if token_id:
        try:
          order_book = client.get_order_book(token_id)
        except py_clob_client.exceptions.PolyApiException as e:
          print(f"Error fetching order book for token {token_id}: {e}")
          continue
        order_books[token_id] = order_book

def main():
  # Create the client
  client = ClobClient(HOST, key=POLYMARKET_KEY, chain_id=CHAIN_ID)
  client.set_api_creds(client.create_or_derive_api_creds())

  today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
  events_pickle_path = f"events_snapshot_{today}.pkl"
  markets_pickle_path = f"markets_snapshot_{today}.pkl"
  # final_pickle_path = f"unified_data_snapshot_{today}.pkl"

  # Check if events pickle exists
  if os.path.exists(events_pickle_path):
    with open(events_pickle_path, 'rb') as f:
      all_events = pickle.load(f)
    print(f"Loaded {len(all_events)} events from {events_pickle_path}")
  else:
    # Fetch Events via "Gamma" (using placeholder method)
    all_events = fetch_all_events_from_gamma()

    # Convert list of events to dictionary with event ID as key
    all_events = {event['id']: event for event in all_events}

  with open(events_pickle_path, 'wb') as f:
    pickle.dump(all_events, f)
  print(f"Saved {len(all_events)} events to {events_pickle_path}")

  # Check if markets pickle exists
  if os.path.exists(markets_pickle_path):
    with open(markets_pickle_path, 'rb') as f:
      all_markets = pickle.load(f)
    print(f"Loaded {len(all_markets)} markets from {markets_pickle_path}")
  else:
    # Fetch Markets via CLOB
    all_markets = fetch_all_markets(client)

    # Convert list of markets to dictionary with market ID as key
    all_markets = {market['condition_id']: market for market in all_markets}

    with open(markets_pickle_path, 'wb') as f:
      pickle.dump(all_markets, f)
    print(f"Saved {len(all_markets)} markets to {markets_pickle_path}")

  # Filter for active, non-closed markets.
  current_markets = {k: v for k, v in all_markets.items() if v['active'] and not v['closed']}
  print(f"Found {len(current_markets)} current markets")

  # Filter for markets ending in the future. Some markets are kept open past their end date due to a dispute in the resolution.
  future_markets = {k: v for k, v in current_markets.items() if v.get('end_date_iso') and v['end_date_iso'] > datetime.now(timezone.utc).isoformat()}
  print(f"Found {len(future_markets)} future markets")

  # Filter for markets ending in the next 7 days.
  near_term_markets = {k: v for k, v in future_markets.items() if v.get('end_date_iso') and v['end_date_iso'] <= (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
  print(f"Found {len(near_term_markets)} near term markets")

  near_non_sports_markets = {k: v for k, v in near_term_markets.items() if v.get('category') and v['category'] != 'Sports'}
  print(f"Found {len(near_non_sports_markets)} near term non-sports markets")

  # Create an edge summary that includes the markets title, prediction json, token outcome, token best ask price, token best ask size and edge.
  edge_summary = []
  for condition_id, market in near_non_sports_markets.items():
    market_title = market.get('title', '')
    market_description = market.get('description', '')
    prediction_json = prediction_pipeline.make_prediction(market_description)
    if not prediction_json:
      continue
    yes_prob = float(prediction_json['probability'])
    
    tokens = market.get('tokens', [])
    for token in tokens:
      outcome = token.get('outcome', '')
      token_id = token.get('token_id', None)
      if token_id:
        try:
          order_book = client.get_order_book(token_id)
          print("Order book:", order_book)
          if order_book.asks:
            best_ask_price = float(order_book.asks[0].price)
            best_ask_size = float(order_book.asks[0].size)
            
            # Calculate edge
            if outcome == 'Yes':
              edge = yes_prob - best_ask_price
            else:  # No
              edge = (1 - yes_prob) - best_ask_price
                
            market_summary = {
              'title': market_title,
              'condition_id': condition_id,
              'probability': prediction_json['probability'],
              'model_confidence': prediction_json['model_confidence'],
              'uncertainty': prediction_json['uncertainty'],
              'token_outcome': outcome,
              'best_ask_price': best_ask_price,
              'best_ask_size': best_ask_size,
              'edge': edge
            }
            edge_summary.append(market_summary)
                  
        except py_clob_client.exceptions.PolyApiException as e:
            print(f"Error fetching order book for token {token_id}: {e}")
            continue
    break
  print("Edge Summary:", edge_summary)
  # Sort edge_summary by largest positive edge
  edge_summary_by_edge = sorted(
      [m for m in edge_summary if m['edge'] > 0],
      key=lambda x: x['edge'],
      reverse=True
  )
  print("Edge Summary sorted by Edge:", edge_summary_by_edge)

  # Sort edge_summary by edge times best_ask_size (expected value)
  edge_summary_by_ev = sorted(
      [m for m in edge_summary if m['edge'] > 0],
      key=lambda x: x['edge'] * x['best_ask_size'],
      reverse=True
  )
  print("Edge Summary sorted by EV:", edge_summary_by_ev)

    # # Build a unified data structure:
    # # Each event can contain its relevant markets,
    # # and each market has its token details + order books.
    # unified_data = {
    #   'events': all_events,
    #   'markets': all_markets,
    #   'order_books': order_books
    # }

    # # Pickle the final unified data
    # with open(final_pickle_path, 'wb') as f:
    #   pickle.dump(unified_data, f)

    # print(f"Saved unified data (events, markets, order books) to {final_pickle_path}")

if __name__ == "__main__":
    main()
