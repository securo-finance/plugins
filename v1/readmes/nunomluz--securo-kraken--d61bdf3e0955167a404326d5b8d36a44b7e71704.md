# Kraken for Securo

A [Securo](https://github.com/securo-finance/securo) plugin that syncs a Kraken spot account through Kraken's REST API. It is read-only: it can't trade, withdraw, or move anything into or out of Earn.

**Beta (0.1.0).** It was built without a Kraken key, from Kraken's documentation and the way other open-source tools read the ledger, so it has not yet been checked against a real account. Please report any quantity or gain that doesn't match what Kraken shows (see "Reporting a problem").

You connect it from **Accounts > + Connect Bank**; it shows under **Bank Connections**, and its records carry the synced badge. Securo matches each record by its Kraken id, so a sync never duplicates anything.

**It needs Securo 0.20.0 or later**, the first release with provider plugins, with plugins enabled.

## What syncs where

- **Fiat balances** (EUR, USD, GBP, ...) become one investment account each, named "Kraken EUR" and so on, with their deposits, withdrawals, fees, rewards and fiat-to-fiat conversions as cash activity. Buying or selling a coin is not cash activity; it belongs to the coin.
- **Coins**, stablecoins and what you hold in Earn included, become **one asset per coin** in a single wallet called "Kraken". Spot and Earn balances are added together (for example `ETH`, `ETH.B` and `ETH2.S` are one ETH asset), and the split is kept in the asset's details.
- **Trades** behind each coin, so cost basis and gains are real, not a snapshot. Units Kraken's history can't explain become one opening buy or an adjustment sell, so the trades always add up to your balance without inventing a gain.
- A coin you sold out stays listed with quantity 0 and keeps its realized gain.

Each Kraken API key is one connection. A Kraken sub-account has its own keys, so add it as another connection.

## Create the Kraken API key

1. In Kraken, open **Security > API** and create a key.
2. Give it **only two permissions: Query Funds and Query Ledger Entries.** Nothing that can trade, withdraw or export is needed.
3. Do not turn on two-factor (OTP) for the key itself; the plugin can't supply a code.
4. Use this key **for Securo only**. Kraken requires every request's nonce to go up, so another program using the same key can lock Securo out.
5. Copy the **API key** and the **Private key**. The private key is shown once.

## Set up Securo

Your Securo instance needs plugins with code turned on. See [Securo's plugin docs](https://docs.usesecuro.com/docs/features/plugins).

1. As the workspace owner, install **Kraken** from the plugin catalog.
2. On **Accounts**, click **+ Connect Bank**, pick **Kraken API key** under "From your plugins", and enter the **API key** and **Private key**. Optionally enter the currency to value your assets in (EUR, USD, GBP, CAD, CHF, AUD or JPY; EUR if empty).
3. The first sync starts on its own. **Sync now** runs another.

The valuation currency is **fixed after the first sync**. To value assets in another currency, add a new connection.

If Kraken rejects the key or it lacks a permission, the connection asks you to fix it: use **Reconnect** and enter a corrected key. Disconnecting removes the accounts and archives the assets, as for any connected bank.

## How cost basis works

The plugin rebuilds each coin's average cost from the ledger. In plain words:

- **Buying** with fiat costs what you paid, fees included. Fiat in another currency than your valuation currency is converted at Kraken's price at that time.
- **Selling** for fiat realizes the difference to the average cost.
- **Swaps** (one coin for another) carry the cost over: the coin you give up leaves at its average cost, so there is no gain, and the coin you receive takes that cost over. The gain appears later, when you sell the new coin for fiat.
- **Rewards and airdrops** (staking, Earn rewards, dividends, forks) cost zero, so they show up as gain. All of one coin's rewards in a calendar month are sent as one trade.
- **Deposits** of a coin from outside are priced at the market price at the time.
- **Withdrawals** of a coin leave at average cost, so moving coins to your own wallet makes no gain. The withdrawal fee is part of what leaves.
- **Balancing trades** cover whatever the ledger can't explain (history Kraken no longer shows, rounding). They are priced so they never create a gain, and are recomputed on every sync.
- Moving a coin between spot and Earn changes nothing: both count in the same asset.

This is meant to show sensible gains, not to produce a tax filing.

## First sync and long histories

Kraken limits how fast the ledger can be read (about 550–600 entries fit in one sync's time budget on a starter account), and Securo stops a sync after 60 seconds. A long history is therefore read over several hourly syncs, newest first. Cash activity shows up as it is collected. **Coins and their trades appear once the whole ledger and the prices they need have been read**; until then Securo leaves your assets alone rather than guessing.

## Limits

- Amounts below 0.000001 of a coin (dust) are lost, because Securo stores six decimals.
- A coin worth less than 0.01 per unit in your valuation currency (SHIB, PEPE and similar), or held in a quantity of a billion or more, is sent with its value and cost only, with no trades: Securo's six-decimal trade prices would otherwise make up gains. Its cost basis is still tracked.
- Legacy ETH staking rewards may be counted twice if Kraken types both of their ledger rows as rewards. The balancing trades keep the quantity right either way, but the reward gain could be overstated.
- Futures, margin and NFTs are not shown as things in Securo. Their effect on your spot balances is recorded (money moved to Futures leaves at average cost, money coming back counts at the market price).
- Fees paid in Kraken fee credits (KFEE) count as zero.
- Prices come from Kraken's public market data. When one can't be fetched, the plugin waits for the next sync instead of failing. When Kraken has no trade after an event (a pair not listed yet, or delisted), the lot takes the first price available later, and keeps it.
- A balancing trade that is no longer needed can't be deleted from Securo, so it stays as a buy of 0.000001 at no cost: a coin you sold out may show a 0.000001 lot.
- Very large histories (roughly 150,000 trades or more) don't fit in one reply: Securo caps a plugin's reply at 16 MB.

## What it can reach

Only `api.kraken.com`, to read your balances and ledger with your key and Kraken's public prices. It calls only `BalanceEx` and `Ledgers` with your key. (The probe below also calls `GetApiKeyInfo`, which needs no permission, to show which permissions the key has.) It has no access to your Securo data: it hands the records back, and Securo writes them. Your key is stored encrypted by Securo and only passed to this plugin. It is never logged.

## Reporting a problem

If a quantity or a gain looks wrong, run the read-only probe and share its output. It prints only the shape of your ledger: entry types, subtypes, asset codes and how entries group, with no amounts, ids or dates beyond the month.

```
$env:KRAKEN_API_KEY = "<api key>"
$env:KRAKEN_API_SECRET = "<private key>"
python tools/kraken_probe.py > probe.txt
```

Read `probe.txt` before sharing it, and use the same two-permission key.

## Development

Standard-library Python only, no runtime dependencies. Tests use pytest against fake HTTP and made-up data:

```
python -m pytest -q
```

`python tools/make_icons.py` regenerates the icons. The icon and logo are an original mark, not Kraken artwork. Kraken is named only to say which service this connects to; the plugin is not affiliated with or endorsed by Kraken.

Design decisions are in [DESIGN.md](DESIGN.md). Licensed under MIT.
