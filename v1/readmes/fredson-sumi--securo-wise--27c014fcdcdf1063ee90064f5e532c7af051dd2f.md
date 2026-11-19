# Wise for Securo

A [Securo](https://github.com/securo-finance/securo) plugin that syncs your [Wise](https://wise.com) account with a **read-only API token**. It can't send or move money.

It works like the banks Securo connects to itself: you connect it from **+ Connect Bank**, it shows under **Bank Connections**, and its records carry the synced badge. Securo writes them, matching each one by its Wise id, so a sync never duplicates anything.

Each sync brings in, for **every profile your token can see**, personal and business alike:

- **Balances**: one account per currency balance ("Wise USD", "Wise Business EUR") and one per Jar ("Wise Jar: Holiday (EUR)"), with Wise's balance.
- **Activity**: card payments, transfers sent and received, money added, and Wise's fees, each on the balance it moved, for the amount that left or reached it (fees included).
- **Conversions and Jar moves**: a debit on one balance and a credit on the other, filed under Securo's **Transfers** category so they don't count as spending or income.

The first sync reads your whole history. A long one takes a few syncs, each continuing where the last stopped. Later syncs re-read the last 30 days, so a pending payment shows up as pending and is updated once Wise completes it. A pending payment Wise cancels drops to 0 and is marked "(cancelled)".

Card payments carry the amount and the merchant's name. Wise doesn't give a token the merchant's category, location or the original foreign amount.

## Who can use it

Wise lets you create an API token only from a **Wise business account**. That token also reads your personal profile. Without a business account:

| Your Wise account | How to get it into Securo |
|---|---|
| Business (with or without a personal profile) | This plugin |
| Personal, in the EU or UK | Securo's built-in **Enable Banking** connection, if it lists Wise for your country |
| Personal, anywhere else | Download a statement from Wise (CSV or QIF) and use Securo's **Import** |

The plugin can't read Wise's balance statements either way: outside the US, Canada, Australia, New Zealand, Singapore and Malaysia, Wise requires an extra verification an API token can't give. It reads the activity feed instead, which on a real account adds up to Wise's balances exactly.

## Set up Wise

1. Sign in to Wise and open **Settings → Integrations and tools → API tokens** ([direct link](https://wise.com/your-account/integrations-and-tools/api-tokens)).
2. **Add new token**, give it a name, and pick **Read only**. Leave "Allowed IPs" empty unless your Securo server has a fixed public IP; if you fill it in, include that IP.
3. Confirm with Wise's 2-step verification and copy the token.

## Set up Securo

Your Securo instance needs plugins with code turned on (`PLUGINS_ENABLED=true` and the `plugins` Compose profile), Securo **0.20.0 or later**. See [Securo's plugin docs](https://docs.usesecuro.com/docs/features/plugins).

1. As the workspace owner, install **Wise** from the plugin catalog.
2. On **Accounts**, click **+ Connect Bank**, pick **Wise API token** under "From your plugins", and paste the token.
3. The first sync starts on its own; **Sync now** under Bank Connections runs another.

If the token stops working (revoked, or Wise refuses it), the connection asks for it again: use **Reconnect** under Bank Connections and paste a new one. Disconnecting removes the accounts, as for any connected bank.

Dates are the day Wise recorded each activity in UTC, so something done late in the evening west of UTC can show the next day.

## What it can reach

- `api.wise.com`, to read your profiles, balances and activity

It has no access to your Securo data: it hands the records back, and Securo writes them. Your token is stored encrypted by Securo and only passed to this plugin.

## Development

```bash
uv run --python 3.14 --group dev pytest -q
```

The plugin itself uses only the Python standard library. [DESIGN.md](DESIGN.md) explains its decisions and [docs/wise-api.md](docs/wise-api.md) what Wise's API returns. Two scripts help look at real data without copying it into the repo:

- `scripts/sample.py` writes a redacted sample of what Wise returns for a token (digits become 9, names become X). It refuses to write inside the repo.
- `scripts/sandbox.py` creates test activity in a Wise sandbox account (`api.wise-sandbox.com`, fake money). It needs a full-access sandbox token.

## License

MIT
