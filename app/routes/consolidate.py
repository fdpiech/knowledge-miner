"""Consolidation/export routes."""

import json

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    flash,
    current_app,
)

from app.models import ConsolidationJob, File, db
from app.consolidator import consolidate_files

consolidate_bp = Blueprint("consolidate", __name__, url_prefix="/consolidate")


@consolidate_bp.route("/", methods=["GET", "POST"])
def consolidate():
    """Handle consolidation form and execution."""
    if request.method == "POST":
        file_ids_raw = request.form.getlist("file_ids")
        file_ids = []
        for fid in file_ids_raw:
            try:
                file_ids.append(int(fid))
            except ValueError:
                continue

        if not file_ids:
            flash("No files selected for consolidation.", "warning")
            return redirect(url_for("consolidate.consolidate"))

        output_format = request.form.get("format", "markdown")
        name = request.form.get("name", "").strip() or "Untitled Export"

        query_params = {
            "file_ids": file_ids,
            "source": "manual_selection",
        }

        output_dir = current_app.config["KCM"]["consolidation"]["output_dir"]

        try:
            job = consolidate_files(
                file_ids=file_ids,
                output_format=output_format,
                name=name,
                db_session=db.session,
                output_dir=output_dir,
                query_params_json=json.dumps(query_params),
            )
            flash(f"Consolidation complete: {job.file_count} files exported.", "success")
            return redirect(url_for("consolidate.history"))
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("consolidate.consolidate"))

    # GET: show consolidation form with selected files if any
    file_ids_raw = request.args.getlist("file_ids")
    file_ids = []
    for fid in file_ids_raw:
        try:
            file_ids.append(int(fid))
        except ValueError:
            continue

    selected_files = []
    if file_ids:
        selected_files = File.query.filter(File.id.in_(file_ids)).all()

    return render_template(
        "consolidate.html",
        selected_files=selected_files,
    )


@consolidate_bp.route("/history")
def history():
    """List past consolidation jobs."""
    jobs = ConsolidationJob.query.order_by(ConsolidationJob.created_at.desc()).all()
    return render_template("consolidate_history.html", jobs=jobs)


@consolidate_bp.route("/download/<int:job_id>")
def download(job_id: int):
    """Download the output file of a consolidation job."""
    job = ConsolidationJob.query.get_or_404(job_id)
    if not job.output_path:
        flash("No output file available for this job.", "warning")
        return redirect(url_for("consolidate.history"))

    return send_file(
        job.output_path,
        as_attachment=True,
    )
