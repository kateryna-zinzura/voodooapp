# tabs/bitly_stats.py
import streamlit as st
import requests
import pandas as pd
import time
from urllib.parse import urlparse, parse_qs
from typing import Optional


# =====================================================================
#                        BITLY API HELPERS
# =====================================================================

def get_group_guid() -> Optional[str]:
    """Fetch the Bitly group GUID (required for listing links)."""
    token = st.secrets["BITLY_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get("https://api-ssl.bitly.com/v4/groups", headers=headers)

    if resp.status_code != 200:
        st.error(f"❌ Could not load Bitly groups: {resp.status_code} — {resp.text}")
        return None

    data = resp.json()
    groups = data.get("groups", [])
    if not groups:
        st.error("❌ No Bitly groups found.")
        return None

    return groups[0]["guid"]


def get_all_bitlinks(group_guid: str, created_after: Optional[int] = None):
    """Fetch links from Bitly, optionally limited by creation time."""
    token = st.secrets["BITLY_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}

    bitlinks = []
    size = 50
    page = 1

    while True:
        params = f"?size={size}&page={page}"
        if created_after:
            params += f"&created_after={created_after}"

        url = f"https://api-ssl.bitly.com/v4/groups/{group_guid}/bitlinks{params}"

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            st.error(f"❌ Bitly API error {resp.status_code}: {resp.text}")
            return []

        data = resp.json()
        items = data.get("links", [])
        bitlinks.extend(items)

        if len(items) < size:  # no more pages
            break

        page += 1

    return bitlinks


def get_clicks(bitlink_id: str) -> int:
    """Fetch total clicks for a Bitly link."""
    token = st.secrets["BITLY_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}

    url = f"https://api-ssl.bitly.com/v4/bitlinks/{bitlink_id}/clicks/summary"
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        return 0

    return resp.json().get("total_clicks", 0)


# =====================================================================
#                        UTM PARSING
# =====================================================================

def parse_utm_params(long_url: str):
    parsed = urlparse(long_url)
    query = parse_qs(parsed.query)

    return {
        "utm_source": query.get("utm_source", [""])[0],
        "utm_medium": query.get("utm_medium", [""])[0],
        "utm_campaign": query.get("utm_campaign", [""])[0],
    }


# =====================================================================
#                        STREAMLIT TAB UI
# =====================================================================

def render():
    st.header("📊 Bitly Statistics Dashboard")

    st.markdown(
        "Filter by **date** and **UTM parameters** to speed up loading. "
        "Pre-filtering avoids unnecessary Bitly API calls."
    )

    # ----------------- Date Range Filter -----------------
    date_choice = st.selectbox(
        "Fetch links from:",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
    )

    now = int(time.time())

    if date_choice == "Last 7 days":
        created_after = now - 7 * 24 * 3600
    elif date_choice == "Last 30 days":
        created_after = now - 30 * 24 * 3600
    elif date_choice == "Last 90 days":
        created_after = now - 90 * 24 * 3600
    else:
        created_after = None

    # ----------------- Pre-fetch Filters -----------------
    st.subheader("⚡ Pre-filter by UTM TEXT (before fetching clicks — VERY fast)")

    prefilter_source = st.text_input("Must contain utm_source text (optional)")
    prefilter_medium = st.text_input("Must contain utm_medium text (optional)")
    prefilter_campaign = st.text_input("Must contain utm_campaign text (optional)")

    st.markdown("---")

    # ----------------- FETCH BUTTON -----------------
    if st.button("Load Bitly Stats", type="primary"):
        with st.spinner("Fetching data from Bitly…"):

            group_guid = get_group_guid()
            if not group_guid:
                return

            links = get_all_bitlinks(group_guid, created_after)

            if not links:
                st.warning("No Bitly links found.")
                return

            rows = []

            for item in links:
                bitlink = item.get("link")
                long_url = item.get("long_url", "")
                title = item.get("title") or "Untitled"

                # ------------------------------------------------------------
                # PRE-FETCH FILTERS (skip early for speed)
                # ------------------------------------------------------------
                if prefilter_source and f"utm_source={prefilter_source}" not in long_url:
                    continue
                if prefilter_medium and f"utm_medium={prefilter_medium}" not in long_url:
                    continue
                if prefilter_campaign and f"utm_campaign={prefilter_campaign}" not in long_url:
                    continue

                # ------------------------------------------------------------
                # PARSE UTM
                # ------------------------------------------------------------
                utm = parse_utm_params(long_url)

                # ------------------------------------------------------------
                # CLICK STAT FETCH (slow — so we avoid it for skipped items)
                # ------------------------------------------------------------
                bitlink_id = bitlink.replace("https://", "")
                clicks = get_clicks(bitlink_id)

                rows.append({
                    "Title": title,
                    "Bitly Link": bitlink,
                    "UTM URL": long_url,
                    "utm_source": utm["utm_source"],
                    "utm_medium": utm["utm_medium"],
                    "utm_campaign": utm["utm_campaign"],
                    "Clicks": clicks,
                })

        if not rows:
            st.warning("No results match your filters.")
            return

        df = pd.DataFrame(rows)

        # ----------------- Sorting -----------------
        df = df.sort_values(
            ["utm_source", "utm_medium", "utm_campaign", "Clicks"],
            ascending=[True, True, True, False]
        )

        st.subheader("📄 Results")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Download Stats as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="bitly_stats.csv",
            mime="text/csv"
        )
