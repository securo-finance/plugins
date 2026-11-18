# Interactive Brokers for Securo

A [Securo](https://github.com/securo-finance/securo) plugin that syncs your Interactive Brokers account through the **Flex Web Service**. It is read-only: it can't place trades or move money.

It works like the banks Securo connects to itself: you connect it from **+ Connect Bank**, it shows under **Bank Connections**, and its records carry the synced badge. Securo writes them, matching each one by its IBKR id, so a sync never duplicates anything.

**Versions 0.2 and later need Securo 0.20.0 or later**, the first release with provider plugins. Securo 0.19.0 can't install them; [version 0.1](https://github.com/fredson-sumi/securo-ibkr/tree/v0.1.0) is the last one that runs there.

Each sync brings in:

- **Cash**: one investment account per currency, with IBKR's ending cash as the balance
- **Cash activity**: deposits, withdrawals, dividends, interest, fees and taxes from the Statement of Funds (trades are left out of spending)
- **Open positions**: one asset per position, valued at IBKR's position value on the statement date
- **Trades**: the buys and sells behind each position, in the asset's transaction history. What you held before the first statement becomes one opening buy, priced at IBKR's cost basis.
- **Closed positions**: an instrument you sold out keeps its trades and realized gain, and stays listed as sold in Securo. Needs the Trades section.

Short positions (such as written options) get an asset and a value, but no trade history: Securo's ledger doesn't hold short positions.

The first sync covers the last 365 days. Later syncs pick up from the last statement. IBKR finalizes Flex data once a day, so the newest day you'll see is yesterday.

## Set up IBKR

1. In the IBKR Portal, go to **Performance & Reports → Flex Queries**.
2. Under **Flex Web Service Configuration**, enable the service and generate a **token**. If you restrict it by IP, allow your Securo server's public IP.
3. Create an **Activity Flex Query** with these settings:
   - **Format: XML** (Text/CSV won't work)
   - **Period: Last 365 Calendar Days.** The plugin sends its own date range with each request, and its first sync asks for that year.
   - Sections and fields:

| Section | Options | Fields to select |
|---|---|---|
| Account Information | | Account ID, Currency, Account Alias or Name |
| Cash Report | Currency breakout | Currency, Ending Cash |
| Statement of Funds | | Currency, Date, Amount (or Debit and Credit), Activity Description (or Activity Code), Transaction ID, Trade ID, Symbol, Balance |
| Open Positions | **Summary** level of detail, not lots | Conid, Symbol, Description, Asset Class, Sub Category, Currency, Position, Multiplier, Mark Price, Position Value, Cost Basis Money, ISIN, Side, Open Date/Time |
| Trades (recommended) | Execution level | Conid, Symbol, Description, Asset Class, Sub Category, Currency, Trade ID, Trade Date, Quantity, Trade Price, Multiplier, Buy/Sell, Open/Close Indicator, Proceeds, Net Cash, IB Commission, IB Commission Currency, Taxes, Realized P/L (FIFO) |

4. Save the query and note its **Query ID**.

## Set up Securo

Your Securo instance needs plugins with code turned on (`PLUGINS_ENABLED=true` and the `plugins` Compose profile). See [Securo's plugin docs](https://docs.usesecuro.com/docs/features/plugins).

This version needs a Securo that syncs plugins as banks ([securo-finance/securo#1461](https://github.com/securo-finance/securo/issues/1461)).

1. As the workspace owner, install **Interactive Brokers** from the plugin catalog.
2. On **Accounts**, click **+ Connect Bank**, pick **IBKR Flex Query** under "From your plugins", and enter the **Flex Web Service token** and the **Activity Flex Query ID**.
3. The first sync starts on its own. A large statement can take IBKR a few minutes to generate; if it isn't ready, the next sync collects it. **Sync now** under Bank Connections asks again.

IBKR publishes each day's activity some hours after that day ends, so the plugin asks for a day from 06:00 UTC the next day. If IBKR is later than that, a sync brings in the days before it and reports nothing wrong; the newest day follows a few hours later.

If the token stops working, use **Reconnect** under Bank Connections and enter a new one. Disconnecting removes the accounts and archives the assets, as for any connected bank.

**Coming from 0.1:** 0.1 wrote ordinary records through Securo's API. After the update, the connection syncs into new, synced records, starting again with the last 365 days; the 0.1 records stay as they were, so delete them once you're happy with the synced ones.

## What it can reach

- `ndcdyn.interactivebrokers.com` and `gdcdyn.interactivebrokers.com`, to request and download your statement

It has no access to your Securo data: it hands the statement's records back, and Securo writes them.

Your token is stored encrypted by Securo and only passed to this plugin.

## Development

```bash
uv run --python 3.14 --group dev pytest -q
```

The plugin itself uses only the Python standard library. [DESIGN.md](DESIGN.md) explains how it maps a statement onto Securo's records and why.

## License

MIT
