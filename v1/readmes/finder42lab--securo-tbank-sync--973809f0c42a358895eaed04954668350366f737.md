# T-Bank Investments for Securo

Базовый provider-плагин импорта брокерских данных Т-Банка в Securo.

## Что импортируется

- денежный счёт на каждую валюту из `OperationsService/GetPositions`;
- неторговые движения как `accounts[].transactions`;
- открытые позиции из `OperationsService/GetPortfolio` как `holdings`;
- покупки и продажи из `GetOperationsByCursor` как `holdings[].trades`;
- названия, тикеры и ISIN через `InstrumentsService/GetInstrumentBy`.

## Используемые API-методы

Все методы вызываются через `POST` относительно
`https://invest-public-api.tbank.ru/rest/`:

```text
tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts
tinkoff.public.invest.api.contract.v1.OperationsService/GetPositions
tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio
tinkoff.public.invest.api.contract.v1.OperationsService/GetOperationsByCursor
tinkoff.public.invest.api.contract.v1.InstrumentsService/GetInstrumentBy
```

`GetOperationsByCursor` читается до `hasNext=false`. Сделки раскрываются из
`items[].tradesInfo.trades`; агрегатные `quantity` и `price` используются как
fallback.

Для облигаций `current_value` включает `currentNkd`. Отрицательные позиции
импортируются по количеству и стоимости, но без `trades`: ledger Securo не
поддерживает short-позиции.

Если `GetPositions` возвращает `limitsLoadingInProgress=true`, синхронизация
завершается временной ошибкой и повторяется позже, не записывая частичный баланс.

Плагин только читает данные. Для подключения нужен read-only токен Invest API.

## Стабильные идентификаторы

```text
cash account: tbank:<account-id>:<currency>
transaction:  tbank:<account-id>:operation:<operation-id>
holding:      tbank:<account-id>:<instrument-uid>
trade:        tbank:<account-id>:trade:<operation-id>:<execution-num>
```

Securo сопоставляет записи по `external_id`, поэтому форматы нельзя менять после
публикации плагина.

## Запуск тестов

```bash
uv run --group dev pytest -q
```

## Перед публикацией

Каркас требует проверки на реальном sandbox/read-only аккаунте:

1. Сверить REST payload актуальной версии Invest API.
2. Проверить валюту и оценку фьючерсов, опционов и облигаций.
3. Проверить распределение общей комиссии операции между частичными исполнениями.
4. Решить, нужны ли закрытые позиции и искусственная opening-сделка для истории старше 365 дней.
5. Добавить `icon.png`, логотип и заменить manifest id `local/securo-tbank`.
