# ING Germany (FinTS) for Securo

A read-only bank provider plugin for [Securo](https://github.com/securo-finance/securo). It connects directly to ING Germany using FinTS and imports checking and Extra account balances and transactions, including pending checking-account transactions when ING provides them. It cannot make payments or transfers.

**This plugin is AI-generated and was developed with AI assistance.** It is an independent, community project and is not affiliated with, endorsed by, or supported by ING or Securo. It has been tested with one live ING connection and is not yet broadly production-verified.

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

## Limitations and privacy

- ING supports Direct Depot data via FinTS. Depot discovery and an empty depot response have been tested, but importing live holdings is **experimental and not yet verified with actual positions**. The plugin reads complete MT535 positions and leaves existing holdings unchanged when a depot reports no positions; missing or incomplete data stops the sync rather than deleting assets. Compare imported positions and valuations with ING.
- ING does not list Rahmenkredit as a supported FinTS account in its current [FinTS FAQ](https://www.ing.de/hilfe/log-in/fints/). This plugin does not implement or verify Rahmenkredit support.
- Interactive TAN or app approval is not implemented. If ING requires a challenge that cannot be completed by this read-only flow, the connection pauses and needs attention.
- The bank's FinTS balance can differ from the balance shown in ING's app, including because of pending items. Do not assume either balance mode matches the app in every situation.
- Avoid syncing the same account simultaneously through multiple providers without reconciling duplicates. Switching providers can create duplicate historical transactions. Do not remove and recreate a plugin connection unnecessarily: its stored ID salt is used to keep transaction IDs stable.
- Login, password or PIN, selected IBANs, and the plugin's persisted FinTS state are stored as Securo plugin secrets. They are not part of this repository. The plugin connects to `fints.ing.de` through Securo's runner and egress proxy. Never post credentials, full IBANs, or bank responses in issues or logs.

## License

The plugin's own code is licensed under [MIT](LICENSE). The `fints` dependency is separately licensed under LGPL-3.0-or-later; its dependencies have their own licenses.
