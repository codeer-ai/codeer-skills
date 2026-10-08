# Billing, refunds, and dispute tasks

## Lifecycle

`quote → authorize → charge/invoice → collect → reconcile → adjust/refund → dispute → close`

## Base tasks

- `BILLING-PRICE-QUOTE`: understand price, estimate, fees, or coverage.
- `BILLING-INVOICE-EXPLAIN`: explain charge components and timing.
- `BILLING-PAY`: choose or change payment method and complete payment.
- `BILLING-STATUS`: verify receipt, balance, credit, or refund state.
- `BILLING-CORRECT`: correct amount, payer, tax, or invoice data.
- `REFUND-ELIGIBILITY`: determine whether refund or credit is allowed.
- `REFUND-INITIATE-CHANGE`: start or modify a refund.
- `DISPUTE-UNRECOGNIZED`: report duplicate, unauthorized, or unknown charges.
- `DISPUTE-OUTCOME`: challenge a denial, fee, valuation, or responsibility decision.

## Task-specific complications

- estimate is mistaken for a guaranteed final amount;
- pending authorization is mistaken for a settled charge;
- refund method or destination differs from original payment;
- partial refund, split payment, credit, or voucher;
- renewal, cancellation, and billing clocks differ;
- customer disputes both service quality and price;
- payer, beneficiary, account owner, and requester differ;
- multiple transactions are conflated;
- chargeback or external dispute is already open.

## Common composites

- cancellation + refund;
- service failure + fee dispute;
- plan change + prorating;
- missing order + charge dispute;
- invoice correction + records request.

## Risk hooks

- direct financial loss;
- unauthorized transaction or fraud;
- regulatory disclosure and consent obligations;
- loss of dispute rights or deadline;
- false price guarantee or unauthorized waiver.

## Recommended cross-task challenges

`CH-MULTIPLE-ENTITIES`, `CH-CONTRADICTION`, `CH-MISSING-EVIDENCE`, `CH-POLICY-PRESSURE`, `CH-DEMANDS-GUARANTEE`, `CH-THREAT-ESCALATION`, `CH-REPEATED-CONTACT`

## Public research signals

Search pricing disclosures, invoices, refund and dispute policies, regulator complaints, court decisions, chargeback guidance, and reviews mentioning surprise fees.
