BEGIN;

CREATE SCHEMA token_distribution;
SET search_path TO token_distribution;

CREATE DOMAIN ethereum_address AS bytea CHECK (bit_length(value) = 160);

CREATE DOMAIN ethereum_tx_hash AS bytea CHECK (bit_length(value) = 256);

CREATE TYPE round_method AS ENUM ('uniform', 'proportional');

CREATE TABLE requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp timestamp with time zone NOT NULL DEFAULT current_timestamp,
    chain_id bigint NOT NULL DEFAULT 8453,
    token_address ethereum_address NOT NULL,
    amount decimal NOT NULL CHECK (amount > 0),
    round_method round_method NOT NULL,
    num_recipients_per_round bigint NOT NULL CHECK (
        num_recipients_per_round >= 0
    ),
    metadata jsonb NOT NULL DEFAULT '{}',
    recipient_token_community ethereum_address NOT NULL,
    period interval NOT NULL DEFAULT '1 day'::interval
);

CREATE TABLE funding_txs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid NOT NULL REFERENCES requests (id),
    timestamp timestamp with time zone NOT NULL DEFAULT current_timestamp,
    hash ethereum_tx_hash NOT NULL,
    sender ethereum_address NOT NULL,
    amount numeric NOT NULL CHECK (amount > 0),
    metadata jsonb NOT NULL DEFAULT '{}',
    UNIQUE (request_id, hash)
);

CREATE TABLE rounds (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid NOT NULL REFERENCES requests (id),
    timestamp timestamp with time zone NOT NULL DEFAULT current_timestamp,
    scheduled timestamp with time zone NOT NULL,
    amount decimal NOT NULL CHECK (amount > 0),
    method round_method,
    num_recipients bigint CHECK (num_recipients >= 0),
    metadata jsonb NOT NULL DEFAULT '{}',
    UNIQUE (request_id, scheduled)
);

CREATE TABLE logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id uuid NOT NULL REFERENCES rounds (id),
    timestamp timestamp with time zone NOT NULL DEFAULT current_timestamp,
    receiver ethereum_address,
    amount decimal NOT NULL CHECK (amount > 0),
    tx_hash bytea,
    fid bigint NOT NULL CHECK (fid > 0),
    points numeric NOT NULL CHECK (points > 0)
);

CREATE VIEW funding_totals AS
SELECT
    request_id,
    sum(amount) AS amount
FROM funding_txs
GROUP BY request_id;

CREATE VIEW round_totals AS
SELECT
    round_id,
    sum(amount) AS amount
FROM logs
GROUP BY round_id;

CREATE VIEW totals AS
SELECT
    r.request_id,
    sum(rt.amount) AS amount
FROM round_totals AS rt
INNER JOIN rounds AS r ON rt.round_id = r.id
GROUP BY r.request_id;

COMMIT;
