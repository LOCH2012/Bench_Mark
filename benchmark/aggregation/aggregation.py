import numpy as np
import pandas as pd

from benchmark.config import BLOCK_SIZE, METRICS_PATH


def df_by_operation(execution_id, group_by: str | None, aggregation):
    df = pd.read_csv(METRICS_PATH / f"{execution_id}_ops.csv")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["latency_ns"] = df["duration"] * 1000 * 1000

    if group_by == "time":
        df["x"] = (df["time"].dt.floor(f"{aggregation}s")).astype(str)
    elif group_by == "step":
        df["step_group"] = df["step_id"] // aggregation * aggregation
        df["x"] = df.apply(lambda row: (row["phase_id"], row["step_group"]), axis=1)
    return df


def df_by_units(execution_id, group_by, aggregation):
    df = pd.read_csv(METRICS_PATH / f"{execution_id}_units.csv")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["latency_ns"] = df["duration"] * 1000 * 1000

    if group_by == "time":
        df["x"] = (df["time"].dt.floor(f"{aggregation}s")).astype(str)
    elif group_by == "step":
        df["step_group"] = df["step_id"] // aggregation * aggregation
        df["x"] = df.apply(lambda row: (row["phase_id"], row["step_group"]), axis=1)
    return df


def build_xy_data(group, value_column, aggregate_by):
    result = {}
    for op in group[aggregate_by].unique():
        sub = group[group[aggregate_by] == op]
        result[op] = {
            "x": sub["x"].tolist(),
            "y": sub[value_column].tolist()
        }
    return result


def format_aggregation_criterion(criterion, value):
    if criterion == "phase_id":
        return f"Фаза {value}"
    elif criterion == "operation_id":
        return f"Операция {value + 1}"
    return str(value)


def build_summary_data(group, value_column, group_by, aggregation):
    result = {}
    for op in sorted(group[group_by].unique()):
        sub = group[group[group_by] == op]
        result[format_aggregation_criterion(group_by, op)] = {
            "x": [format_aggregation_criterion(aggregation, x) for x in sub[aggregation].tolist()],
            "y": sub[value_column].tolist()
        }
    return result


def aggregate_throughput_summary(execution_id, metric, group_by, aggregation_by):
    if metric.startswith("latency"):
        df = df_by_units(execution_id, None, None)
    else:
        df = df_by_operation(execution_id, None, None)

    gb = [group_by, aggregation_by] if group_by != aggregation_by else [group_by]
    group = df.groupby(gb)[fields_by_metric(metric)]
    group = group_metric(group, metric)

    return build_summary_data(group, "x", group_by, aggregation_by)


def aggregate_throughput_per_steps(execution_id, group_by="step", metric="mbps", aggregation=5):
    df = df_by_operation(execution_id, group_by, aggregation)

    group = df.groupby(["operation_type", "x"])[fields_by_metric(metric)].sum().reset_index()
    group = group_metric(group, metric)

    return build_xy_data(group, "x", "operation_type")


def fields_by_metric(metric):
    if metric == "iops" or metric == "mbps":
        return ["duration", "bytes"]
    elif metric == "errors":
        return ["is_failed"]
    elif metric.startswith("latency"):
        return ["latency_ns"]


def group_metric(group, metric):
    if metric == "iops":
        group = group.sum().reset_index()
        group["x"] = group["bytes"] / BLOCK_SIZE / group["duration"]
    elif metric == "mbps":
        group = group.mean().reset_index()
        group["x"] = group["bytes"] / (1024 ** 2) / group["duration"]
    elif metric == "errors":
        group = group.sum().reset_index()
        group["x"] = group["is_failed"]
    elif metric.startswith("latency"):
        if metric == "latency_max":
            group = group.agg(latency_ns=("latency_ns", "max")).reset_index()
        elif metric == "latency_p99":
            group = group.agg(latency_ns=("latency_ns", lambda x: np.percentile(x, 99))).reset_index()
        elif metric == "latency_p95":
            group = group.agg(latency_ns=("latency_ns", lambda x: np.percentile(x, 95))).reset_index()
        else:
            group = group.mean().reset_index()
        group["x"] = group["latency_ns"]
    return group
