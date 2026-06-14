#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import datetime
from core import compute

app = Flask(__name__)


@app.route("/")
def index():
    today = datetime.date.today()
    return render_template("index.html", today_month=today.month, today_year=today.year)


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()

    def int_list(key):
        raw = data.get(key, [])
        if isinstance(raw, list):
            return [int(x) for x in raw if x is not None]
        return []

    try:
        result = compute(
            month=int(data.get("month", datetime.date.today().month)),
            year=int(data.get("year", datetime.date.today().year)),
            holiday_days=int_list("holiday_days"),
            vipin_leave_days=int_list("vipin_leave_days"),
            himangi_leave_days=int_list("himangi_leave_days"),
            vipin_attended_days=int_list("vipin_attended_days"),
            himangi_attended_days=int_list("himangi_attended_days"),
            vipin_planned_days=int_list("vipin_planned_days"),
            himangi_planned_days=int_list("himangi_planned_days"),
            vipin_wfh_days=int_list("vipin_wfh_days"),
            himangi_wfh_days=int_list("himangi_wfh_days"),
            vipin_done_manual=int(data.get("vipin_done_manual", 0)),
            himangi_done_manual=int(data.get("himangi_done_manual", 0)),
        )
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5050)
