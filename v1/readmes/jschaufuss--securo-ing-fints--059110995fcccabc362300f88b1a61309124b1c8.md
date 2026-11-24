# ING Germany (FinTS) for Securo

A read-only bank provider plugin for [Securo](https://github.com/securo-finance/securo). It connects directly to ING Germany using FinTS and imports checking and Extra account balances and transactions, including pending checking-account transactions when ING provides them. It cannot make payments or transfers.

**This plugin is AI-generated and was developed with AI assistance.** It is an independent, community project and is not affiliated with, endorsed by, or supported by ING or Securo. It has been tested with one live ING connection and is not yet broadly production-verified.

## Approach and alternatives

This plugin aims to represent the data ING returns over FinTS as directly as Securo's bank-provider contract allows. It uses ING-provided text for payees and descriptions without merchant-specific cleanup or renaming. It does normalize whitespace, limit field lengths, select among available fields and generate salted IDs, so the displayed data is not a byte-for-byte copy of the bank's response. Securo's own settings and rules can also affect what is displayed.

The plugin does not apply its own heuristic to pair pending entries with booked transactions. Securo may still match them during synchronization, and that matching can fail when ING changes the date or description; see the pending limitation below.

For a different approach, [Marceltov's ING FinTS plugin](https://github.com/Marceltov/securo-ing-fints) offers formatted merchant names and transaction descriptions, and attempts to match pending entries to booked transactions. Its matching uses transaction details rather than a verified shared bank reference, and its pending cleanup has specific Securo configuration requirements; consult its documentation for the trade-offs and setup.

## Before you start

- Securo **0.20.0 or later**, with plugins enabled and the code plugin runner and egress proxy configured. An administrator must enable these services; see the [Securo bank provider guide](https://github.com/securo-finance/securo/blob/v0.20.0/docs/plugins/bank-provider-plugins.md).
- An ING Germany online banking login and password or Internet banking PIN.
- A valid FinTS product ID registered for the software using the [Deutsche Kreditwirtschaft registration process](https://www.fints.org/de/hersteller/produktregistrierung). An ING customer ID, account number, or email address is not a FinTS product ID. No product ID is supplied with this plugin.
- A successful ING online banking login within the previous 90 days, as required by [ING's FinTS guidance](https://www.ing.de/hilfe/log-in/fints/).

## Install in Securo

1. Open your **personal workspace** and go to **Plugins → Catalog**.
2. Find **ING Germany (FinTS)**, review the requested network access, and install it.
3. Create an ING connection and enter your login, password or PIN, and registered FinTS product ID.
4. To select specific accounts, enter their full IBANs in **Account IBANs to sync**, separated by commas. Leave it empty to request all accounts ING reports. If an account does not support balance retrieval, select only the checking and Extra accounts you want to sync.
5. Start a sync and compare the accounts, balances, and several transactions with ING before relying on the result.

The plugin must first be published to the catalog used by your Securo instance before it appears in the catalog. Availability in the public catalog is not guaranteed.

## Settings

- **Account IBANs to sync:** Optional, comma-separated complete IBANs. An IBAN not returned by ING stops the sync. The field is stored as a plugin secret.
- **Balance mode:** `booked` by default. `pending` selects the additional pending balance reported by ING for checking accounts, if present; it does not calculate a balance from individual transactions. ING's terminology and balance timing can differ from its app. Verify both modes against ING before relying on them. Extra accounts use their booked balance.
- **Transaction history days:** Optional; defaults to 85, accepts 1–89. The sync also respects Securo's requested start date.
- **Experimental depot fetch:** Set to `yes` to discover ING Direct Depot accounts and read their holdings independently of the selected cash accounts. Off by default.

To show pending transactions, enable **Import pending transactions** in Securo's connection settings. The plugin marks the separately returned pending entries as pending; Securo decides whether to import them. Transaction data may change when an entry is booked, so verify that pending entries are matched or cleared and watch for duplicates. Pending amounts may already be reflected in the selected balance; do not subtract them again without checking.

### Known limitation: pending transactions and balances

Pending transactions do not always transition to booked in Securo. ING can report a different date or description after booking, and the pending entry may remain alongside the booked entry even after ING stops returning it. Transactions with the same amount can be separate purchases; do not merge them based on amount alone. Disabling **Import pending transactions** prevents importing new pending entries, but may not remove entries already imported.

As a temporary workaround, disable **Import pending transactions** and use balance mode `booked` for a balance consistent with booked transactions. Alternatively, `pending` may show a balance that already reflects pending amounts, but those amounts will not be visible in the transaction list when pending imports are disabled. Actual balance semantics depend on ING's response; compare with ING before relying on either mode.

**To do:** Investigate whether ING provides a stable, unique reference across pending and booked FinTS records, compare a pending record with its later booked form without collecting credentials or full bank responses, and verify Securo's update behavior. Only implement automatic matching when it is unambiguous, with tests covering repeated amounts, changed dates and descriptions, missing references, and duplicate references. Document any cases requiring manual review. See [issue #1](https://github.com/jschaufuss/securo-ing-fints/issues/1).

## Limitations and privacy

- ING supports Direct Depot data via FinTS. Importing a live position has been observed; depot support remains **experimental**. Depots are read separately and a valid empty depot does not block positions from other depots. The plugin requires a complete MT535 envelope; missing or incomplete answers do not replace holdings. Securo may archive positions that disappear from a complete holdings response. Unit prices are included only when supported fields with matching currency are available. Purchase costs are not imported because their interpretation has not been verified; tickers are not inferred from ISINs. Compare positions and valuations with ING.
- ING does not list Rahmenkredit as a supported FinTS account in its current [FinTS FAQ](https://www.ing.de/hilfe/log-in/fints/). This plugin does not implement or verify Rahmenkredit support.
- Interactive TAN or app approval is not implemented. If ING requires a challenge that cannot be completed by this read-only flow, the connection pauses and needs attention.
- The bank's FinTS balance can differ from the balance shown in ING's app, including because of pending items. Do not assume either balance mode matches the app in every situation.
- Avoid syncing the same account simultaneously through multiple providers without reconciling duplicates. Switching providers can create duplicate historical transactions. Do not remove and recreate a plugin connection unnecessarily: its stored ID salt is used to keep transaction IDs stable.
- Login, password or PIN, selected IBANs, and the plugin's persisted FinTS state are stored as Securo plugin secrets. They are not part of this repository. The plugin connects to `fints.ing.de` through Securo's runner and egress proxy. Never post credentials, full IBANs, or bank responses in issues or logs.

## License

The plugin's own code is licensed under [MIT](LICENSE). The `fints` dependency is separately licensed under LGPL-3.0-or-later; its dependencies have their own licenses.
