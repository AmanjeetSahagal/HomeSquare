from flask import Blueprint, jsonify, request
from ..scraper import scrape_listing

main = Blueprint("main", __name__)

@main.route("/api/analyze_ai", methods=["POST"])
def analyze_home():
    data = request.json
    listing_url = data.get("url")
    listing_data = scrape_listing(listing_url)

    return jsonify({
        "status":"success",
        "data": listing_data
    })