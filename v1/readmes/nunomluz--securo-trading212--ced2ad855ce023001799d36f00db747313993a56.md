# Trading 212 for Securo

A [Securo](https://github.com/securo-finance/securo) plugin that syncs a Trading 212 Invest or Stocks ISA account through Trading 212's public API. It is read-only: it can't place orders, edit pies or move money.

**Beta (0.1.0).** It has not yet been checked against a real account, so please report any position or gain that doesn't match what the Trading 212 app shows.

It works like the banks Securo connects to itself: you connect it from **+ Connect Bank**, it shows under **Bank Connections**, and its records carry the synced badge. Securo writes them, matching each one by its Trading 212 id, so a sync never duplicates anything.

**It needs Securo 0.20.0 or later**, the first release with provider plugins, with plugins enabled.

Each sync brings in:

- **Cash**: one investment account per connection, with your total cash (available, in pies and reserved for orders) as the balance
- **Cash activity**: deposits, withdrawals, dividends, interest and fees (buys and sells are left out of spending)
- **Open positions**: one asset per position, valued at Trading 212's current value, in your account currency
- **Trades**: the buys and sells behind each position. Units the history can't explain (transfers in, stock splits and other corporate actions, shares from before the API's reach) become one opening buy, or an adjustment sell, so the trades always add up to the position. These are priced from what Trading 212 says the position cost, so they don't invent a gain, and they are corrected on every sync.
- **Closed positions**: an instrument you sold out keeps its trades and realized gain, and stays listed as sold in Securo.

Each Trading 212 API key belongs to one account. If you have both an Invest and a Stocks ISA account, create a key for each and add two connections.

## Set up Trading 212

1. In the Trading 212 app, open the **API settings** and create an API key.
2. Give it **read-only permissions** only: account, portfolio, history (orders, dividends, transactions) and metadata. Nothing that can trade is needed.
3. Copy the **API key** and **API secret**. The secret is shown once.

To try the plugin without real money, create the key in a practice account and use the `demo` environment below.

## Set up Securo

Your Securo instance needs plugins with code turned on. See [Securo's plugin docs](https://docs.usesecuro.com/docs/features/plugins).

1. As the workspace owner, install **Trading 212** from the plugin catalog.
2. On **Accounts**, click **+ Connect Bank**, pick **Trading 212 API key** under "From your plugins", and enter the **API key** and **API secret**. Leave **Environment** empty for a live account, or enter `demo` for a practice account.
3. The first sync starts on its own. **Sync now** under Bank Connections runs another.

Long histories take several syncs to catch up. Trading 212 allows about 20 history pages a minute, and Securo stops a sync after 60 seconds, so each hourly sync reads as many pages as it can and carries on where it stopped. Cash activity shows up as it is collected. **Holdings and trades appear once the trade history has caught up**; until then Securo leaves your holdings alone rather than guessing.

If the key stops working or is missing a permission, the connection asks you to fix it: use **Reconnect** under Bank Connections and enter a corrected key. Disconnecting removes the accounts and archives the assets, as for any connected bank.

## What it can reach

- `live.trading212.com`, for a live account
- `demo.trading212.com`, for a practice account

It has no access to your Securo data: it hands the account's records back, and Securo writes them. Your key and secret are stored encrypted by Securo and only passed to this plugin. They are never logged.

## Development

Standard-library Python only, no runtime dependencies. Tests use pytest against fake HTTP and made-up data:

```
python -m pytest -q
```

To try a local copy in Securo, build a catalog index with Securo's `build_index.py` as described in [Writing a plugin](https://docs.usesecuro.com/docs/features/plugins/authoring). `python tools/make_icons.py` regenerates the icons.

The icon and logo are an original mark, not Trading 212 artwork. Trading 212 is named only to say which service this connects to; the plugin is not affiliated with or endorsed by Trading 212.

Design decisions are in [DESIGN.md](DESIGN.md). Licensed under MIT.
