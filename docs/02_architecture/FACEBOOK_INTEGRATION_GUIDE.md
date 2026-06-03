# Facebook API Integration Guide

This document outlines the specific requirements, technical implementations, and common pitfalls regarding the Facebook Ads and Graph API integration for the Marketing Agent OS.

## 1. Facebook App Modes (Development vs. Live)

*   **Live Mode is Required for Ads:** To successfully create Ad Campaigns, Ad Sets, and Ad Creatives via the API, the Facebook App **MUST** be set to **Live** mode. 
*   **Development Mode Limitations:** If the app is in Development mode, the API may silently fail to create valid Ads or return placeholder Ad IDs that cannot be mapped properly in the database.
*   **App Review Compliance:** To maintain Live mode and pass Facebook's App Review, all public-facing pages (Privacy Policy, Terms of Service, Homepage) MUST NOT contain references to "AI-generated content" or similar terminology. The UI should present the app as a standard marketing management tool. Privacy and ToS pages are embedded from Google Sites (e.g., `https://sites.google.com/view/topvnsport/privacy`).

## 2. API Response Parsing (Python SDK)

When using the `facebook_business` Python SDK, the API responses (like `FacebookResponse` or `AdAccount.create_ad`) are **not** standard Python dictionaries.

*   **Do NOT do this:** `ad_id = response.get('id')`
*   **Do this:** `ad_id = response.json().get('id')`

**Technical Detail:** The `FacebookResponse` object wraps the underlying JSON payload. You must call `.json()` on the response object to retrieve the dictionary representation before attempting to extract keys like `id`. Failing to do so will result in `Ad ID None` errors during the batch creation callbacks, which breaks the MAB (Multi-Armed Bandit) tracking.

## 3. Shopee Link Injection

The marketing application is configured to drive traffic specifically to the TOPVNSPORT Shopee store.

*   **Automated Injection:** The destination link `https://shopee.vn/topvnsport` is automatically appended/injected into all Facebook posts and Ad Creatives at the generation or publishing stage.
*   **No Manual Formatting Needed:** AI Agents and prompt templates do not need to manually generate or include the link. The `fb_client.py` and celery tasks (`tasks.py`) ensure the link is properly appended to the `message` or `body` of the Ad Creative.

## 4. Multi-Armed Bandit (MAB) Tracking

*   The extraction of the correct `ad_id` from the Facebook API is critical.
*   The `ad_id` is mapped to the internal `variant_id` in the PostgreSQL database.
*   The cron jobs fetch analytics for the `ad_id` and use this mapping to feed performance data back into the MAB engine to optimize future content generation.
