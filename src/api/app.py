"""
Flask API for company monitoring

This API allows Chrome extension to add/manage companies to monitor
"""

import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from .company_service import CompanyService

# CSRF protection not needed: stateless API with no session/cookie auth
# CORS restricts origins to Chrome extension only - programmatic client, not browser forms
app = Flask(__name__)  # NOSONAR

# Enable CORS - configurable via environment variable
# Default: Chrome extension and localhost only for security
CORS_ORIGINS = os.getenv("FLASK_CORS_ORIGINS", "chrome-extension://*,http://localhost:*")
cors_origins_list = [origin.strip() for origin in CORS_ORIGINS.split(",")]
CORS(app, resources={r"/*": {"origins": cors_origins_list}})

# Initialize service
company_service = CompanyService()


@app.route("/")
def home():
    """API health check"""
    return jsonify(
        {
            "status": "ok",
            "message": "Job Agent Company Monitoring API",
            "version": "1.0",
            "endpoints": {
                "POST /add-company": "Add a company to monitor",
                "GET /companies": "List all monitored companies",
                "GET /company/<id>": "Get a specific company",
                "POST /company/<id>/toggle": "Enable/disable monitoring",
            },
        }
    )


@app.route("/add-company", methods=["POST"])
def add_company():
    """
    Add a company to monitor

    Expected JSON body:
    {
        "name": "Boston Dynamics",
        "careers_url": "https://...",
        "notes": "Optional notes"
    }
    """
    data = request.json

    # Validate required fields
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    if "name" not in data or "careers_url" not in data:
        return (
            jsonify({"success": False, "error": "Missing required fields: name, careers_url"}),
            400,
        )

    # Add company via service
    result = company_service.add_company(
        name=data["name"], careers_url=data["careers_url"], notes=data.get("notes", "")
    )

    if result["success"]:
        return jsonify(result), 201  # 201 Created
    else:
        return jsonify(result), 409  # 409 Conflict (duplicate)


@app.route("/companies", methods=["GET"])
def get_companies():
    """
    Get all monitored companies

    Query params:
        active_only (bool): If true, only return active companies (default: true)
    """
    active_only = request.args.get("active_only", "true").lower() == "true"

    companies = company_service.get_all_companies(active_only=active_only)

    return jsonify({"success": True, "count": len(companies), "companies": companies})


@app.route("/company/<int:company_id>", methods=["GET"])
def get_company(company_id):
    """Get a specific company by ID"""
    company = company_service.get_company(company_id)

    if company:
        return jsonify({"success": True, "company": company})
    else:
        return jsonify({"success": False, "error": "Company not found"}), 404


@app.route("/company/<int:company_id>/toggle", methods=["POST"])
def toggle_company(company_id):
    """Toggle company active status"""
    new_status = company_service.toggle_active(company_id)

    return jsonify({"success": True, "active": new_status})


if __name__ == "__main__":
    # Run development server
    # Only accessible from localhost for security
    # Debug mode controlled by FLASK_DEBUG environment variable (default: False)
    # Set FLASK_DEBUG=1 or FLASK_DEBUG=true for local development
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
