#!/usr/bin/env python3
import os
import dotenv
import pickle
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

def fetch_all_markets(client):
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

def filter_markets_by_end_date(markets, days=7):
  now = datetime.now(timezone.utc)
  end_date = now + timedelta(days=days)
    
  filtered_markets = []
  for market in markets:
      if 'end_date_iso' not in market or not isinstance(market['end_date_iso'], str):
          continue
      market_end = datetime.fromisoformat(market['end_date_iso'].replace('Z', '+00:00'))
      if now <= market_end <= end_date:
          filtered_markets.append(market)
            
  return filtered_markets
def filter_markets_by_category(markets, category=None, exclude=False):
  if not category:
      return markets
        
  filtered_markets = []
  for market in markets:
      market_category = market.get('category', '')
      if (not exclude and market_category == category) or (exclude and market_category != category):
          filtered_markets.append(market)
            
  return filtered_markets

def main():
  # Create CLOB client and get/set API credentials
  client = ClobClient(HOST, key=POLYMARKET_KEY, chain_id=CHAIN_ID)
  client.set_api_creds(client.create_or_derive_api_creds())

  # Check for existing pickle from today
  today = datetime.now().strftime('%Y-%m-%d')
  pickle_path = f'all_markets_{today}.pkl'
    
  if os.path.exists(pickle_path):
      with open(pickle_path, 'rb') as f:
          all_markets = pickle.load(f)
      print(f"Loaded {len(all_markets)} markets from pickle")
  else:
      # Fetch all markets using CLOB API
      all_markets = fetch_all_markets(client)
      # Save to pickle
      with open(pickle_path, 'wb') as f:
          pickle.dump(all_markets, f)
    
  print(f"Total markets: {len(all_markets)}")
  print("Example Market:", all_markets[0])
  print("iso:", all_markets[0]['end_date_iso'])

  # Filter for markets ending in next X days
  days = 1
  upcoming_markets = filter_markets_by_end_date(all_markets, days=days)
  print(f"\nMarkets ending in next {days} days: {len(upcoming_markets)}")

  # Filter out sports markets
  filtered_markets = filter_markets_by_category(upcoming_markets, category="Sports", exclude=True)
  print(f"\nMarkets after category filtering: {len(filtered_markets)}")
  print("-" * 50)

  # Sort by end date
  filtered_markets.sort(key=lambda x: x['end_date_iso'])
    
  for market in filtered_markets:
      end_date = datetime.fromisoformat(market['end_date_iso'].replace('Z', '+00:00'))
      print(f"Question: {market['question']}")
      print(f"Ends: {end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
      print(f"Condition ID: {market['condition_id']}")
      print(f"Category: {market.get('category', 'N/A')}")
        
      # Get order book for both tokens
      for token in market['tokens']:
          token_id = token['token_id']
          outcome = token['outcome']
          order_book = client.get_order_book(token_id)
          print(f"\nOutcome: {outcome}")
          print(f"Token ID: {token_id}")
          print(f"Order Book: {order_book}")
      print("-" * 50)

if __name__ == "__main__":
  main()
