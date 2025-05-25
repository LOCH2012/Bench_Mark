import re

import yaml
from flask import Flask, render_template, flash, redirect, url_for, request

from benchmark.config import STORAGE_CONFIG
from benchmark.metrics.metric_reporter import metricFileReporter
from benchmark.model.execution import ExecutionRequest
from benchmark.model.profile import BenchmarkProfile, ProfilePhase
from benchmark.repository.profile import profiles, profile_to_yaml, yaml_to_profile
from benchmark.repository.reports import reports
from benchmark.web.api_blueprint import api_blueprint
from benchmark.workload.executor import BENCHMARK_EXECUTOR

app = Flask(__name__)
app.secret_key = 'very-secret-key'
app.register_blueprint(api_blueprint, url_prefix="/api")


@app.route("/", endpoint='home')
def _index():
    return render_template("pages/index.html")


@app.route("/benchmarks/start")
def _get_start_benchmark():
    return render_template("pages/benchmark.html", profiles=profiles.list())


@app.route("/benchmarks/start", methods=["POST"])
def _post_start_benchmark():
    profile_name = request.form.get('profile_name')
    profile = profiles.get(profile_name)
    exec_conf = ExecutionRequest(profile_name=profile_name, profile=profile, storage_configuration=STORAGE_CONFIG)
    try:
        execution_id = BENCHMARK_EXECUTOR.execute(exec_conf, metricFileReporter)
        flash(f"Бенчмарк запущен", "success")
        return redirect(url_for("_get_benchmark_status", execution_id=execution_id))
    except Exception as e:
        flash(f"Ошибка запуска: {e}", "error")
    return redirect(url_for('_get_start_benchmark'))


@app.route("/benchmarks")
def _get_benchmark_list():
    executions = BENCHMARK_EXECUTOR.all_executions()
    return render_template("pages/benchmark_list.html", executions=executions.items())


@app.route("/benchmark_status")
def _get_benchmark_status():
    execution_id = request.args.get('execution_id')
    status = BENCHMARK_EXECUTOR.status(execution_id)
    summary = reports.get_summary(execution_id)
    return render_template("pages/benchmark_status.html", execution_id=execution_id, exec_status=status, summary=summary)


@app.route("/benchmark_status", methods=["POST"])
def _post_interrupt_benchmark():
    execution_id = request.form.get('execution_id')
    try:
        BENCHMARK_EXECUTOR.interrupt(execution_id)
        flash(f"Бенчмарк прерван", "success")
    except Exception as e:
        flash(f"Ошибка прерывания: {e}", "error")
    return redirect(url_for('_get_benchmark_status', execution_id=execution_id))


@app.route("/profiles")
def _get_profile_list():
    return render_template("pages/profile_list.html", profiles=profiles.list())


@app.route("/profiles/edit")
def _get_profile_editor():
    profile_name = request.args.get('profile_name')
    profile = profiles.get_raw(profile_name)
    if not profile:
        flash(f"Profile {profile_name} not found", "error")
        return redirect(url_for('_get_profile_list'))
    return render_template("pages/profile_editor.html",
                           profile_text=profile, profile_name=profile_name)


@app.route("/profiles/edit", methods=["POST"])
def _post_profile_editor():
    profile_name = request.form.get('profile_name')
    profile_text = request.form.get('profile_text')
    try:
        yaml_to_profile(profile_text)
    except yaml.YAMLError as e:
        flash(f"Ошибка парсинга yaml: {e}", "error")
        return render_template("pages/profile_editor.html",
                               profile_text=profile_text, profile_name=profile_name)

    profiles.set(profile_name, profile_text)
    flash(f"Профиль {profile_name} сохранен", "success")
    return render_template( "pages/profile_editor.html",
                           profile_text=profile_text, profile_name=profile_name)


@app.route("/profiles/create")
def _get_profile_editor_create():
    profile_name = request.args.get('profile_name')
    if re.match('^[A-Za-z0-9_.]+$', profile_name) is None:
        flash(f"Profile name {profile_name} is not valid, use only letters, numbers and underscore", "error")
        return redirect(url_for('_get_profile_list'))

    profile_text = profile_to_yaml(BenchmarkProfile(phases=[ProfilePhase(duration_sec=10)]))
    return render_template("pages/profile_editor.html",
                           profile_text=profile_text, profile_name=profile_name)


@app.route("/reports")
def _get_report_list():
    return render_template("pages/report_list.html", reports=reports.list())


@app.route("/reports/report")
def _get_report_summary():
    report_name = request.args.get('report_name')
    summary = reports.get_summary(report_name)
    if not summary:
        flash(f"Report {report_name} not found", "error")
        return redirect(url_for('_get_report_list'))
    return render_template("pages/report_summary.html", report_name=report_name, summary=summary)


def run_app():
    app.run(debug=True, host="0.0.0.0")
