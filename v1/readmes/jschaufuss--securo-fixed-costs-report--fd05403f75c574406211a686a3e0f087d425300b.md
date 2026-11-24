# Fixed Costs and Subscriptions for Securo

A report plugin for Securo 0.21.0 or newer. It detects possible recurring expenses and shows estimated monthly costs, annualized costs, the largest monthly equivalent, payment details, a category breakdown and a six-month estimated-cost trend. The annualized figure is 12 times the current monthly estimate, not a forecast of exact future payments. When enough history is available, the monthly estimate also shows its change from the previous month.

> [!WARNING]
> This plugin was developed with AI assistance. Its detection is heuristic and can miss payments or identify ordinary purchases as recurring costs. Review the results before relying on them for financial decisions.

## Screenshots

The report overview shows estimated costs and possible recurring payments:

![Report overview and recurring payments](docs/screenshots/report-overview.png)

The category breakdown and trend show how estimated costs are distributed and change over time:

![Category breakdown and estimated monthly cost trend](docs/screenshots/category-and-trend.png)

## Using the report

The workspace owner can install the plugin from a compatible plugin catalog. Enable Securo's plugin runner (`plugins` profile), then add **Fixed costs and subscriptions** from the reports library. The plugin requests read access to transactions and categories. It has no external dependencies and declares no network access.

Choose a sufficiently long period. Securo passes only the transactions in that period to the report, with a limit of 731 days and 20,000 transactions. Short periods may not contain enough history. Securo 0.21.0 can reject its own 2Y preset because the preset starts at the beginning of a month and can exceed the 731-day report limit. Use a custom range spanning at most 731 days. The report warns when the input is truncated.

## How detection works

The report groups posted debits by payee and account. It looks for roughly monthly, quarterly, half-yearly, or yearly intervals and similar amounts, tolerating occasional missed payments and unrelated transactions. Amazon Prime descriptions are considered separately from other Amazon purchases. Monthly and annual series require at least two payments; quarterly and half-yearly series require at least three. A monthly series must end in the current or previous calendar month and its last two payments must fall in consecutive months. Longer intervals remain active until seven days after their next inferred due date. Historical reports use the earlier of today and the selected end date as the reference. A recurring purchase can be mistaken for a subscription, and changing payee names or amounts and irregular intervals can prevent detection. An established series can include a latest payment with a substantially changed amount; such rows are flagged for review. The monthly equivalent uses the latest amount divided by its interval; it is an estimate, not a confirmed contract or a list of active subscriptions. To reduce false positives for busy merchants, a monthly candidate with other transactions from the same payee and account must contain at least three payments, explain more than half of that payee’s eligible transactions and cover at least two thirds of the months in which that payee has transactions, within the most recent 183 days of the selected period. This may hide a real subscription when the same merchant has many other purchases. These heuristics can still mistake unrelated payments for a recurring series.

The category table groups monthly equivalents by the category of the latest payment. The trend independently runs detection with only transactions available through each month, using the monthly equivalent as known then. It shows at most six months in the selected range. Months without enough detected evidence are blank rather than zero; early estimates can miss quarterly or annual payments when the selected history is too short. It is an estimate, not a complete historical contract ledger.

Ignored transactions and categories, categories marked as transfers, split-category transactions, and foreign-currency transactions without a converted amount are excluded. The most recent 400 transactions are examined for each payee and account; the report displays a warning when this limit may apply. Securo does not provide paired-transfer flags or every reporting exclusion to plugins, so some transactions excluded from standard reports may still be included. Securo's report input does not provide group shares or existing recurring bills. Suggestions cannot be confirmed or edited in the report.

## Installation and publication

The plugin is published at [jschaufuss/securo-fixed-costs-report](https://github.com/jschaufuss/securo-fixed-costs-report). Securo discovers public repositories with the `securo-plugin` topic and a published release; its catalog is rebuilt every six hours. Once indexed, find it under **Plugins** in Securo and install it as the workspace owner. See the [Securo plugin documentation](https://docs.usesecuro.com/docs/features/plugins) for the runner setup and installation details.

## Tests

Run the unit tests with:

```sh
python3 -m unittest discover -s tests -v
```

The integration test uses the real Securo 0.21.0 runner and its test fixtures. After installing development dependencies in a Securo checkout, run from its `backend` directory:

```sh
export FIXED_COSTS_PLUGIN_DIR=/absolute/path/to/securo-fixed-costs-report
cp "$FIXED_COSTS_PLUGIN_DIR/tests/securo_integration/test_fixed_costs_integration.py" tests/test_local_fixed_costs.py
.venv/bin/python -m pytest tests/test_local_fixed_costs.py -q --no-cov
rm tests/test_local_fixed_costs.py
```

The integration test validates the original manifest, installs the plugin in an isolated test catalog, and requests a report through Securo's API and plugin runner. It uses synthetic data and does not connect to a bank.
