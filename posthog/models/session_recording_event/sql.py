from django.conf import settings

from posthog.clickhouse.kafka_engine import KAFKA_COLUMNS, kafka_engine, ttl_period
from posthog.clickhouse.table_engines import Distributed, MergeTreeEngine, ReplacingMergeTree, ReplicationScheme
from posthog.kafka_client.topics import KAFKA_SESSION_RECORDING_EVENTS
from posthog.models.kafka_engine_dlq.sql import KAFKA_ENGINE_DLQ_BASE_SQL, KAFKA_ENGINE_DLQ_MV_BASE_SQL

SESSION_RECORDING_EVENTS_DATA_TABLE = (
    lambda: "sharded_session_recording_events" if settings.CLICKHOUSE_REPLICATION else "session_recording_events"
)

SESSION_RECORDING_EVENTS_TABLE_BASE_SQL = """
CREATE TABLE IF NOT EXISTS {table_name} ON CLUSTER '{cluster}'
(
    uuid UUID,
    timestamp DateTime64(6, 'UTC'),
    team_id Int64,
    distinct_id VARCHAR,
    session_id VARCHAR,
    window_id VARCHAR,
    snapshot_data VARCHAR,
    created_at DateTime64(6, 'UTC')
    {materialized_columns}
    {extra_fields}
) ENGINE = {engine}
{partition_by}
{order_by}
{ttl_period}
{settings}
"""

MATERIALIZED_COLUMNS = {
    "has_full_snapshot": {
        "schema": "Int8",
        "materializer": "MATERIALIZED JSONExtractBool(snapshot_data, 'has_full_snapshot')",
    },
    "events_summary": {
        "schema": "Array(String)",
        "materializer": "MATERIALIZED JSONExtract(JSON_QUERY(snapshot_data, '$.events_summary[*]'), 'Array(String)')",
    },
    "click_count": {
        "schema": "Int8",
        "materializer": "MATERIALIZED length(arrayFilter((x) -> JSONExtractInt(x, 'type') = 3 AND JSONExtractInt(x, 'data', 'source') = 2 AND JSONExtractInt(x, 'data', 'source') = 2, events_summary))",
    },
    "keypress_count": {
        "schema": "Int8",
        "materializer": "MATERIALIZED length(arrayFilter((x) -> JSONExtractInt(x, 'type') = 3 AND JSONExtractInt(x, 'data', 'source') = 5, events_summary))",
    },
    "timestamps_summary": {
        "schema": "Array(DateTime64(6, 'UTC'))",
        "materializer": "MATERIALIZED arraySort(arrayMap((x) -> toDateTime(JSONExtractInt(x, 'timestamp') / 1000), events_summary))",
    },
    "first_event_timestamp": {
        "schema": "DateTime64(6, 'UTC')",
        "materializer": "MATERIALIZED arrayReduce('min', timestamps_summary)",
    },
    "last_event_timestamp": {
        "schema": "DateTime64(6, 'UTC')",
        "materializer": "MATERIALIZED arrayReduce('max', timestamps_summary)",
    },
    "urls": {
        "schema": "Array(String)",
        "materializer": "MATERIALIZED arrayFilter(x -> x != '', arrayMap((x) -> JSONExtractString(x, 'data', 'href'), events_summary))",
    },
}


# Like "has_full_snapshot Int8 MATERIALIZED JSONExtractBool(snapshot_data, 'has_full_snapshot') COMMENT 'column_materializer::has_full_snapshot'"
SESSION_RECORDING_EVENTS_MATERIALIZED_COLUMNS = ", " + ", ".join(
    f"{column_name} {column['schema']} {column['materializer']}" for column_name, column in MATERIALIZED_COLUMNS.items()
)

# Like "has_full_snapshot Int8 COMMENT 'column_materializer::has_full_snapshot'"
SESSION_RECORDING_EVENTS_PROXY_MATERIALIZED_COLUMNS = ", " + ", ".join(
    f"{column_name} {column['schema']} COMMENT 'column_materializer::{column_name}'"
    for column_name, column in MATERIALIZED_COLUMNS.items()
)


SESSION_RECORDING_EVENTS_MATERIALIZED_COLUMN_COMMENTS_SQL = lambda: """
    ALTER TABLE session_recording_events
    ON CLUSTER '{cluster}'
    COMMENT COLUMN has_full_snapshot 'column_materializer::has_full_snapshot'
""".format(
    cluster=settings.CLICKHOUSE_CLUSTER
)

SESSION_RECORDING_EVENTS_DATA_TABLE_ENGINE = lambda: ReplacingMergeTree(
    "session_recording_events", ver="_timestamp", replication_scheme=ReplicationScheme.SHARDED
)
SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: SESSION_RECORDING_EVENTS_TABLE_BASE_SQL.format(
    table_name=SESSION_RECORDING_EVENTS_DATA_TABLE(),
    cluster=settings.CLICKHOUSE_CLUSTER,
    materialized_columns=SESSION_RECORDING_EVENTS_MATERIALIZED_COLUMNS,
    extra_fields=KAFKA_COLUMNS,
    engine=SESSION_RECORDING_EVENTS_DATA_TABLE_ENGINE(),
    order_by="ORDER BY (team_id, toHour(timestamp), session_id, timestamp, uuid)",
    partition_by="PARTITION BY toYYYYMMDD(timestamp)",
    ttl_period=ttl_period(),
    settings="SETTINGS index_granularity = 512",
)

KAFKA_SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: SESSION_RECORDING_EVENTS_TABLE_BASE_SQL.format(
    table_name="kafka_session_recording_events",
    cluster=settings.CLICKHOUSE_CLUSTER,
    engine=kafka_engine(topic=KAFKA_SESSION_RECORDING_EVENTS),
    materialized_columns="",
    extra_fields="",
    order_by="",
    partition_by="",
    ttl_period="",
    settings="SETTINGS kafka_handle_error_mode='stream'",
)

KAFKA_SESSION_RECORDING_EVENTS_DLQ_SQL = lambda: KAFKA_ENGINE_DLQ_BASE_SQL.format(
    table=f"{settings.CLICKHOUSE_DATABASE}.kafka_session_recording_events_dlq",
    cluster=settings.CLICKHOUSE_CLUSTER,
    engine=MergeTreeEngine("kafka_session_recording_events_dlq", replication_scheme=ReplicationScheme.REPLICATED),
)

KAFKA_SESSION_RECORDING_EVENTS_DLQ_MV_SQL = lambda: KAFKA_ENGINE_DLQ_MV_BASE_SQL.format(
    view_name=f"{settings.CLICKHOUSE_DATABASE}.kafka_session_recording_events_dlq_mv",
    target_table=f"{settings.CLICKHOUSE_DATABASE}.kafka_session_recording_events_dlq",
    kafka_table_name=f"{settings.CLICKHOUSE_DATABASE}.kafka_session_recording_events",
)

SESSION_RECORDING_EVENTS_TABLE_MV_SQL = lambda: """
CREATE MATERIALIZED VIEW session_recording_events_mv ON CLUSTER '{cluster}'
TO {database}.{target_table}
AS SELECT
uuid,
timestamp,
team_id,
distinct_id,
session_id,
window_id,
snapshot_data,
created_at,
_timestamp,
_offset
FROM {database}.kafka_session_recording_events
""".format(
    target_table=(
        "writable_session_recording_events"
        if settings.CLICKHOUSE_REPLICATION
        else SESSION_RECORDING_EVENTS_DATA_TABLE()
    ),
    cluster=settings.CLICKHOUSE_CLUSTER,
    database=settings.CLICKHOUSE_DATABASE,
)


# Distributed engine tables are only created if CLICKHOUSE_REPLICATED

# This table is responsible for writing to sharded_session_recording_events based on a sharding key.
WRITABLE_SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: SESSION_RECORDING_EVENTS_TABLE_BASE_SQL.format(
    table_name="writable_session_recording_events",
    cluster=settings.CLICKHOUSE_CLUSTER,
    engine=Distributed(data_table=SESSION_RECORDING_EVENTS_DATA_TABLE(), sharding_key="sipHash64(distinct_id)"),
    extra_fields=KAFKA_COLUMNS,
    materialized_columns="",
    order_by="",
    partition_by="",
    ttl_period="",
    settings="",
)

# This table is responsible for reading from session_recording_events on a cluster setting
DISTRIBUTED_SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: SESSION_RECORDING_EVENTS_TABLE_BASE_SQL.format(
    table_name="session_recording_events",
    cluster=settings.CLICKHOUSE_CLUSTER,
    engine=Distributed(data_table=SESSION_RECORDING_EVENTS_DATA_TABLE(), sharding_key="sipHash64(distinct_id)"),
    extra_fields=KAFKA_COLUMNS,
    materialized_columns=SESSION_RECORDING_EVENTS_PROXY_MATERIALIZED_COLUMNS,
    order_by="",
    partition_by="",
    ttl_period="",
    settings="",
)


INSERT_SESSION_RECORDING_EVENT_SQL = (
    lambda: f"""
INSERT INTO {SESSION_RECORDING_EVENTS_DATA_TABLE()} (uuid, timestamp, team_id, distinct_id, session_id, window_id, snapshot_data, created_at, _timestamp, _offset)
SELECT %(uuid)s, %(timestamp)s, %(team_id)s, %(distinct_id)s, %(session_id)s, %(window_id)s, %(snapshot_data)s, %(created_at)s, now(), 0
"""
)


TRUNCATE_SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: (
    f"TRUNCATE TABLE IF EXISTS {SESSION_RECORDING_EVENTS_DATA_TABLE()} ON CLUSTER '{settings.CLICKHOUSE_CLUSTER}'"
)

DROP_SESSION_RECORDING_EVENTS_TABLE_SQL = lambda: (
    f"DROP TABLE IF EXISTS {SESSION_RECORDING_EVENTS_DATA_TABLE()} ON CLUSTER '{settings.CLICKHOUSE_CLUSTER}'"
)

UPDATE_RECORDINGS_TABLE_TTL_SQL = lambda: (
    f"ALTER TABLE {SESSION_RECORDING_EVENTS_DATA_TABLE()} ON CLUSTER '{settings.CLICKHOUSE_CLUSTER}' MODIFY TTL toDate(created_at) + toIntervalWeek(%(weeks)s)"
)
