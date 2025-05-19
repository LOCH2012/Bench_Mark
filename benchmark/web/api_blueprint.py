from flask import Blueprint, request, jsonify

from benchmark.aggregation.aggregation import aggregate_throughput_per_steps, aggregate_throughput_summary

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/results/summary/throughput")
def get_result_summary_throughput():
    execution_id = request.args.get("execution_id")
    metric = request.args.get("metric", "mbps")
    group_by = request.args.get("group_by", "phase_id")
    aggregation = request.args.get("aggregation", "operation_type")
    data = aggregate_throughput_summary(execution_id, metric, group_by, aggregation)
    return jsonify(data)


@api_blueprint.route("/results/dynamic/throughput")
def get_result_throughput():
    execution_id = request.args.get("execution_id")
    group_by = request.args.get("group_by", "step")
    metric = request.args.get("metric", "mbps")
    aggregation = int(request.args.get("aggregation", "5"))
    data = aggregate_throughput_per_steps(execution_id, group_by, metric, aggregation)
    return jsonify(data)
