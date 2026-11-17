# Order and fulfillment tasks

## Lifecycle

`discover/select → quote/cart → order → authorize/pay → allocate → ship/perform → deliver → return/replace → close`

## Base tasks

- `ORDER-PRODUCT-FIT`: compare items, variants, availability, or service packages.
- `ORDER-CREATE`: place or complete an order.
- `ORDER-CONFIRM`: verify items, quantity, price, address, and status.
- `ORDER-MODIFY`: change item, quantity, address, delivery, or recipient.
- `ORDER-CANCEL`: stop an order before an irreversible transition.
- `ORDER-TRACK`: check fulfillment and delivery state.
- `ORDER-MISSING-DAMAGED`: report missing, wrong, incomplete, or damaged fulfillment.
- `ORDER-RETURN-REPLACE`: initiate return, exchange, redelivery, or repair.

## Task-specific complications

- modification requested after allocation or shipment;
- confirmation differs from customer expectation;
- partial shipment or multiple packages;
- address, recipient, or identity mismatch;
- stock changed between selection and order;
- delivery marked complete but not received;
- return window, condition, or evidence is disputed;
- third-party seller, carrier, or installer owns the next action;
- duplicate orders or charges;
- multiple products have different states.

## Common composites

- tracking + address change;
- missing delivery + refund;
- damaged item + warranty;
- cancellation + payment reversal;
- product fit + stock availability.

## Risk hooks

- financial loss or duplicate fulfillment;
- delivery to the wrong or unsafe location;
- loss of return or warranty rights;
- unsafe product, recall, or installation;
- responsibility gap across merchant, carrier, and marketplace.

## Recommended cross-task challenges

`CH-LATE-CRITICAL-DETAIL`, `CH-MULTIPLE-ENTITIES`, `CH-CONTRADICTION`, `CH-THIRD-PARTY`, `CH-MISSING-ATTACHMENT`, `CH-POLICY-PRESSURE`, `CH-REPEATED-CONTACT`

## Public research signals

Search help centers, delivery promises, return rules, recall notices, marketplace responsibility policies, carrier complaints, and reviews about missing or damaged orders.
