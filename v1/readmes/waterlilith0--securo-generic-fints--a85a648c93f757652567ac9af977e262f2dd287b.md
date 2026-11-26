# German FinTS for Securo

A read-only Securo plugin for syncing accounts, balances, and posted transactions from supported German banks over FinTS. It is based on the ING FinTS plugin and extends it with additional bank profiles. It does not initiate payments or transfers.

## Requirements

- Securo 0.20.0 or later, with the code plugin runner and egress proxy enabled.
- A German bank account with FinTS PIN/TAN access.

## Supported bank profiles

Enter a profile key in **Bank profile**. A bank code (BLZ) is required unless noted.

| Profile | Bank/provider | BLZ |
| --- | --- | --- |
| `atruvia` | Atruvia | Required |
| `atruvia-1` | Atruvia | Required |
| `gls` | GLS Bank | Fixed: `43060967` |
| `ing` | ING Germany | Fixed: `50010517` |
| `gad` | Legacy GAD | Required |
| `comdirect` | comdirect | Required |
| `deutsche-bank` | Deutsche Bank | Required |
| `dkb` | DKB | Required |

## Setup

Install the plugin from your Securo plugin catalog and create a bank connection. Enter the profile, BLZ if required, FinTS user ID, and online banking PIN or password.

Optionally, provide comma-separated account IBANs to sync only selected accounts, and set the transaction history window (1 to 89 days; default 85). Leave the IBAN field empty to sync all eligible accounts returned by the bank. Use a separate connection for each bank.

Check the imported balances and transactions against your bank. FinTS features vary by bank, so not every account or TAN method is guaranteed to work. App-based approvals may be required during a sync; typed TAN challenges are not supported.

## Privacy and limitations

Credentials, selected IBANs, and FinTS client state are stored as Securo plugin secrets. Network access is restricted to the bank hosts declared in the plugin manifest.

Only accounts, balances, and posted transactions are supported. Investment/depot accounts and bank-specific extensions are not implemented.

## License

The plugin code is licensed under [MIT](LICENSE). The `fints` dependency is licensed under LGPL-3.0-or-later; its dependencies have their own licenses.
