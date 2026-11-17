# Appointment and access tasks

## Lifecycle

`discover service → check fit/availability → request → hold → confirm → prepare → change/cancel → attend/no-show → follow-up`

## Base tasks

- `APPT-SERVICE-FIT`: determine whether the provider, location, format, or service is appropriate.
- `APPT-AVAILABILITY`: find available dates, times, people, or locations.
- `APPT-CREATE`: create a booking with required details.
- `APPT-CONFIRM`: verify that a booking exists and confirm its terms.
- `APPT-RESCHEDULE`: change time, provider, location, attendee, or service.
- `APPT-CANCEL`: cancel and understand consequences.
- `APPT-LATE-NOSHOW`: report delay, missed arrival, or re-entry.
- `APPT-WAITLIST`: join, leave, or respond to a waitlist.
- `APPT-PREPARE`: understand prerequisites, documents, payment, or preparation.

## Task-specific complications

- requested slot or provider is unavailable;
- original booking cannot be found;
- duplicate or overlapping bookings;
- reschedule or cancellation deadline has passed;
- requested provider cannot perform the requested service;
- multiple attendees, dependents, pets, assets, or services are linked;
- tentative hold is mistaken for confirmation;
- different parties provide conflicting booking details;
- the apparent booking request hides a time-sensitive need;
- the customer requests priority, insertion, or a policy exception.

## Common composites

- service fit + availability;
- urgent advice + appointment request;
- reschedule + fee dispute;
- records transfer + first appointment;
- cancellation + refund.

## Risk hooks

- harmful delay caused by treating urgency as ordinary scheduling;
- wrong provider, service, location, or preparation;
- lost entitlement or cancellation charge;
- privacy disclosure to an unauthorized scheduler;
- failure to confirm an action that leaves the customer unserved.

## Recommended cross-task challenges

`CH-AMBIGUOUS-REFERENCE`, `CH-SELF-CORRECTION`, `CH-CONFLICTING-CONSTRAINTS`, `CH-FRAGMENTED-MULTITURN`, `CH-THIRD-PARTY`, `CH-POLICY-PRESSURE`, `CH-REPEATED-CHANGE`

## Public research signals

Search booking pages, preparation instructions, cancellation policies, reviews mentioning phone or booking failures, urgent-access guidance, and complaints about waits or missed confirmations.
