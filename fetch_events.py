#!/usr/bin/env python3
import os
import dotenv
import pickle
import requests

from datetime import datetime, timedelta, timezone
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY

# Event Keys: dict_keys(
# ['id', 'ticker', 'slug', 'title', 'description', 'resolutionSource',
# 'endDate', 'image', 'icon', 'active', 'closed', 'archived', 'new', 'featured', 'restricted', 'liquidity',
# 'volume', 'openInterest', 'createdAt', 'updatedAt', 'competitive', 'volume24hr', 'enableOrderBook',
# 'liquidityAmm', 'liquidityClob', 'commentCount', 'markets', 'series', 'tags', 'cyom', 'showAllOutcomes',
# 'showMarketImages', 'enableNegRisk', 'automaticallyActive', 'seriesSlug', 'negRiskAugmented'])

# Market Keys: dict_keys(['id', 'question', 'conditionId', 'slug', 'resolutionSource', 'endDate',
# 'liquidity', 'startDate', 'image', 'icon', 'description', 'outcomes', 'outcomePrices', 'volume',
# 'active', 'closed', 'marketMakerAddress', 'createdAt', 'updatedAt', 'new', 'featured', 'submitted_by',
# 'archived', 'resolvedBy', 'restricted', 'groupItemTitle', 'groupItemThreshold', 'questionID', 'enableOrderBook',
# 'orderPriceMinTickSize', 'orderMinSize', 'volumeNum', 'liquidityNum', 'endDateIso', 'startDateIso', 'hasReviewedDates',
# 'volume24hr', 'clobTokenIds', 'umaBond', 'umaReward', 'volume24hrClob', 'volumeClob', 'liquidityClob',
# 'acceptingOrders', 'negRisk', 'ready', 'funded', 'acceptingOrdersTimestamp', 'cyom', 'competitive',
# 'pagerDutyNotificationEnabled', 'approved', 'clobRewards', 'rewardsMinSize', 'rewardsMaxSpread', 'spread',
# 'lastTradePrice', 'bestBid', 'bestAsk', 'automaticallyActive', 'clearBookOnStart', 'manualActivation', 'negRiskOther'])

env = dotenv.dotenv_values(".env")
HOST = "https://clob.polymarket.com"
POLYMARKET_KEY = env["PK"]
CHAIN_ID = POLYGON

def fetch_all_active_events():
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

def filter_events_by_end_date(events, days=7):
  now = datetime.now(timezone.utc)
  end_date = now + timedelta(days=days)
    
  filtered_events = []
  missing_end_date = 0
  for event in events:
    if 'endDate' not in event:
      print("No end date for event")
      missing_end_date += 1
      continue
    event_end = datetime.fromisoformat(event['endDate'].replace('Z', '+00:00'))
    if now <= event_end <= end_date:
      filtered_events.append(event)
  print("Total missing end dates:", missing_end_date)
            
  return filtered_events
def filter_events_by_order_book(events, enableOrderBook=True):
  filtered_events = []
  missing_order_book = 0
  for event in events:
    if 'enableOrderBook' not in event:
      print("No orderBook flag for event")
      missing_order_book += 1
      continue
    if event['enableOrderBook'] == enableOrderBook:
      filtered_events.append(event)
  print("Total missing orderBook flags:", missing_order_book)
            
  return filtered_events
def filter_events_by_tag(events, tag_key, tag_value, exclude=False):
  filtered_events = []
  missing_tags = 0
  for event in events:
    if 'tags' not in event:
      print("No tags for event")
      missing_tags += 1
      continue
      
    tag_match = False
    for tag in event['tags']:
      if tag.get(tag_key) == tag_value:
        tag_match = True
        break
        
    if (not exclude and tag_match) or (exclude and not tag_match):
      filtered_events.append(event)
            
  print("Total events missing tags:", missing_tags)
  return filtered_events

def main():
  # Create CLOB client and get/set API credentials
  client = ClobClient(HOST, key=POLYMARKET_KEY, chain_id=CHAIN_ID)
  client.set_api_creds(client.create_or_derive_api_creds())

  # Check for existing pickle from today
  today = datetime.now().strftime('%Y-%m-%d')
  pickle_path = f'all_events_{today}.pkl'
    
  if os.path.exists(pickle_path):
    with open(pickle_path, 'rb') as f:
      all_events = pickle.load(f)
    print(f"Loaded {len(all_events)} events from pickle")
  else:
    # Fetch all active events
    all_events = fetch_all_active_events()
    # Save to pickle
    with open(pickle_path, 'wb') as f:
      pickle.dump(all_events, f)
    
  print(f"Total active events: {len(all_events)}")
  # Filter for events ending in next X days
  days = 1
  upcoming_events = filter_events_by_end_date(all_events, days=days)
  print(f"\nEvents ending in next {days} days: {len(upcoming_events)}")
  # Filter for events with order book enabled
  order_book_events = filter_events_by_order_book(upcoming_events)
  print(f"\nEvents with order book enabled: {len(order_book_events)}")
  # Filter for events with tag
  tag_key = "label"
  tag_value = "Sports"
  tagged_events = filter_events_by_tag(order_book_events, tag_key, tag_value, exclude=True)
  print(f"\nEvents after tag filtering: {len(tagged_events)}")
  print("-" * 50)

  # Sort by end date
  upcoming_events.sort(key=lambda x: x['endDate'])
    
  for event in tagged_events:
    end_date = datetime.fromisoformat(event['endDate'].replace('Z', '+00:00'))
    print(f"Title: {event['title']}")
    print(f"Ends: {end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    for market in event["markets"]:
      print("Market Title:", market["question"])
      print("Market bestBid:", market.get("bestBid", "N/A"))
      print("Market bestAsk:", market.get("bestAsk", "N/A"))
      print("Market CLOB Token IDs:", market.get("clobTokenIds", "N/A"))
    print("-" * 50)

if __name__ == "__main__":
  main()
