# prediction-trader
A prototype of an LLM pipeline for assessing prediction markets.

## Introduction
After reading about superforecasting and its formulaic approach to generating predictions, I wanted to attempt 
automating the process. I saw in internal competitions that LLMs provided good baseline prediction values with 
individuals scoring highly in internal company markets with the assistance of LLMs. I was interested to see how 
a simple approach would perform in Polymarket prediction markets.

## Pipeline Overview
This Pipeline uses the Polymarket API to retrieve current prediction markets ending in the near future. It then 
feeds the market description into a prompt and API call to the Perplexity API. Perplexity is a search engine 
that creates AI generated responses to user queries based on a RAG database built from a recent crawl of the web. 
The result from this API is a report with underlying citations. This report is treated as an executive summary 
of relevant market information and fed to a large reasoning LLM that is instructed to create a prediction of 
the market outcome. This prediction is then compared to the current market price and a score is generated.

This is done inside a single python notebook (markets.ipynb) that pretty prints a user report that can guide 
the user in making manual trades on the marketplace.

## Initial Results and Thoughts
This was a very fun project. It's interesting to see the model's reasoning for the market prediction and the 
APIs and prices for model intelligence have gotten cheap enough and fast enough to make this a viable project. 
My initial personal analysis of the markets was that there may be some opportunity to automatically trade some 
types of markets. Polymarket has recently expanded their political market offerings (e.g. bets on votes from 
individual senators: [Will Bernie Sanders vote to confirm Tulsi Gabbard](https://polymarket.com/event/which-
senators-will-vote-to-confirm-tulsi-gabbard)) and even includes markets for trading on conspiracy theories 
(e.g. [Was the JFK assassination an inside job](https://polymarket.com/event/was-jfk-assassination-an-inside-job-
march-31?tid=1742326836894)). The LLMs seem to have grounded opinions on these markets. These markets are also 
more diverse and nuanced in their events and criteria compared to other types of traditional betting markets.

The more traditional betting markets include things like sports betting and bets on economic outcomes like 
interest rates and stock market movement. Another type of bet are weather forecasts. All of these market types 
have a long tradition of data science and mature systems in place for forecasting. It's no surprise, but my
initial analysis is that LLMs do not have an advantage in these markets.

I noticed many markets are not well defined and are frequently disputed for days while an insider group of UMA 
cryptocurrency holders decide the outcome. These markets are volatile as arguments are made for and against a 
resolution outcome in the comments. While it's possible to dig in and do research on similar market 
resolutions, it's not a trivial task. It's also possible to join the UMA discord and read the arguments from 
coin holders who are the ultimate arbiters of the market. What's interesting about these markets are the 
volatile prices and the near-term resolution combine for great annualized ROI if one could successfully trade 
them. Organized groups seem to brigade the comment section and pump-and-dump trades during these periods of 
uncertainty. I attempted to manually trade these markets, it seemed like the reasoning LLM had good intuition 
but it's no small task finding and monitoring these markets. One example was a market betting on whether the US 
president would sign an executive order on a specific date [Will Trump issue an executive order on February 4?]
(https://polymarket.com/event/will-trump-issue-an-executive-order-on-february-4/will-trump-issue-an-executive-
order-on-february-4). A White House press release contained a date typo that triggered a dispute with news 
sources disagreeing with the WH press release. The market ultimately resolved in favor of the news outlet 
reported dates, which likely biased:
 * 1) Avoiding ambiguous and contested markets
 * 2) Avoiding insider trading
 * 3) Avoiding markets with mature competition
 * 4) Aggregating all relevant context for the market into a report the LLM could consume.

The best use case for LLMs would probably be in automatically triaging new markets and flagging potential 
opportunities to an experienced trader who could take over collecting information and potentially working with 
the LLM to make a prediction from there.

## How To Run
You will need API keys for the Polymarket CLOB API, the Perplexity API and Google Gemini API. Add these keys 
to a .env file in the root directory with the following format:
PK=""
GEMINI_API_KEY=""
PERPLEXITY_API_KEY=""

Launch a Jupyter notebook server and run the notebook markets.ipynb.
```
$ python -m jupyter notebook markets.ipynb 
```

Run all cells (Note: the first run on each day will take significantly longer than subsequent runs. 
Marketplaces, reports, predictions are all pickled and cached to disk to speed up subsequent runs during early 
development. You can override this behavior by setting the cache variable to None anywhere in the pipeline you 
want fresh data.)

Have fun trading on the market report!