# ING Germany (FinTS) for Securo

A read-only [Securo](https://github.com/securo-finance/securo) plugin for ING Germany. It imports checking and Extra account balances and transactions, including pending checking-account transactions when available. Experimental Direct Depot holdings are optional. It cannot make payments or transfers.

**AI-generated and developed with AI assistance.** This independent community project is not affiliated with or supported by ING or Securo. It has been tested with one live ING connection and is not yet broadly production-verified.

## Approach

The plugin aims for a clear, traceable transaction list based on ING's FinTS data. It does not rename merchants or guess which pending entry belongs to a booked transaction, including on Securo 0.22 and later. It does normalize whitespace, limit field lengths, select available fields and generate salted IDs; Securo settings and rules may also change what you see.

For merchant formatting and heuristic pending-to-booked matching, see [Marceltov's ING FinTS plugin](https://github.com/Marceltov/securo-ing-fints) and its documentation for the associated trade-offs.

## Requirements

- Securo **0.20.0 or later**, with plugins, the runner and egress proxy enabled. See the [bank provider guide](https://github.com/securo-finance/securo/blob/v0.20.0/docs/plugins/bank-provider-plugins.md).
- Your ING Germany login and online banking password or PIN.
- Your own registered FinTS product ID, obtained through [Deutsche Kreditwirtschaft](https://www.fints.org/de/hersteller/produktregistrierung). An ING customer ID, account number or email address is not a product ID; the plugin does not supply one.
- A successful ING online banking login within the previous 90 days, as described in [ING's FinTS guidance](https://www.ing.de/hilfe/log-in/fints/).

## Installation

1. In your personal Securo workspace, open **Plugins → Catalog** and install **ING Germany (FinTS)** after reviewing its network access.
2. Create a connection with your ING login, password or PIN, and FinTS product ID.
3. Optionally enter the complete IBANs of the accounts to sync, separated by commas. Leave the field empty to request all available accounts. If an account does not support balance retrieval, select only the checking and Extra accounts you want to sync.
4. Run a sync and compare the accounts, balances and several transactions with ING.

## Settings

| Setting | Behavior |
| --- | --- |
| Account IBANs to sync | Optional, comma-separated full IBANs. An IBAN ING does not return stops the sync. Stored as a plugin secret. |
| Balance mode | `booked` by default; `pending` selects ING's additional pending balance for checking accounts when available. Extra accounts use the booked balance. |
| Transaction history days | Defaults to 85; accepts 1–89 and respects Securo's requested start date. |
| Experimental depot fetch | Set to `yes` to read Direct Depot holdings independently of the selected cash accounts. Off by default. |

Compare balances with ING before relying on either mode. The pending balance is provided by ING, not calculated from the imported pending transactions.

### Delayed transfers and balances

FinTS data can lag behind the ING app, even for an internal transfer that has already reached the destination account. In one observed late-evening transfer, FinTS still returned the previous checking-account balance and neither transfer entry; the entries appeared on the next day's sync. Extending the transaction query to the following day did not reveal them earlier. This is one observed case, not a guaranteed delay or timing rule.

When ING later supplies both entries, Securo can import and pair them as a transfer. Securo also reconciles a connected account's automatically created opening balance against the imported entries and the bank balance. Pairing and timing are not guaranteed: compare both accounts and balances with ING, and check for duplicates before entering anything manually. Neither balance mode can reflect data ING has not supplied through FinTS.

## Pending transactions

Enable **Import pending transactions** in the connection settings to show pending entries. ING may report a different date or description when a transaction is booked, so a pending entry can remain beside its posted counterpart, even after ING stops returning it. Do not assume equal amounts are duplicates. Disabling pending imports stops new pending entries but may not remove existing ones.

For a balance consistent with booked transactions, disable pending imports and use balance mode `booked`. Alternatively, `pending` may show a balance that includes pending amounts even when those entries are not imported. Compare the result with ING; don't subtract pending amounts again without checking.

Securo 0.22 introduced `complete_feed` to remove eligible pending entries missing from a complete feed. **This plugin does not currently declare it:** feed completeness must first be verified. The feature does not establish a match with a particular booked transaction, and Securo may retain entries with user edits or protected links. We continue to avoid heuristic matching.

Possible future work: investigate stable ING references, verify feed completeness and Securo's behavior, and test repeated amounts, changed dates and descriptions, and missing or duplicate references. See [issue #1](https://github.com/jschaufuss/securo-ing-fints/issues/1).

## Limitations and privacy

- **Depot:** Experimental. One live position has been observed. Depots are read separately; incomplete responses do not replace holdings, but Securo may archive positions missing from a complete response. A matching-currency unit price is preferred; otherwise an indicative per-unit value is derived from total value and quantity when possible. This is not necessarily a market quote. For piece-based holdings, a single unambiguous structured FinTS `70E::HOLD` field with a same-currency entry price is multiplied by quantity to supply total cost; other formats and currencies are not guessed. Tickers are not inferred from ISINs. Securo may not show a provider's unit price as its current market price or its cost as an average price. Compare positions, cost basis and values with ING, especially after transfers, partial sales or currency conversions.
- **Rahmenkredit:** Not supported; ING does not list it in its [FinTS FAQ](https://www.ing.de/hilfe/log-in/fints/).
- **Approval:** Interactive TAN or app approval during sync is not implemented. A connection requiring a challenge pauses and needs attention.
- **Connections:** Syncing an account through multiple providers or switching providers can create duplicate history. Avoid recreating a connection unnecessarily: its saved salt keeps transaction IDs stable.
- **Secrets:** Login, PIN, selected IBANs and FinTS state are stored as Securo plugin secrets, not in this repository. The plugin connects only to `fints.ing.de` via Securo's runner and egress proxy. Never post credentials, full IBANs or bank responses in issues or logs.

## License

The plugin is licensed under [MIT](LICENSE). Its `fints` dependency is LGPL-3.0-or-later; other dependencies have their own licenses.
