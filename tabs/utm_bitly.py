# tabs/utm_bitly.py
import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import Optional, Tuple


# ------------------------------------------------------------------
#                     UTM BUILDER
# ------------------------------------------------------------------

def build_utm_url(
    base_url: str,
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    utm_term: str = "",
) -> str:

    if not base_url:
        return ""

    parsed = urlparse(base_url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    utm_params = {
        "utm_source": utm_source or None,
        "utm_medium": utm_medium or None,
        "utm_campaign": utm_campaign or None,
        "utm_term": utm_term or None,
    }

    for k, v in utm_params.items():
        if v:
            query_params[k] = v

    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


# ------------------------------------------------------------------
#                     BITLY SHORTENER
# ------------------------------------------------------------------

def shorten_with_bitly(long_url: str, domain: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Step 1: Create Bitly short link."""
    bitly_token = st.secrets["BITLY_TOKEN"]

    headers = {
        "Authorization": f"Bearer {bitly_token}",
        "Content-Type": "application/json",
    }

    payload = {"long_url": long_url}
    if domain:
        payload["domain"] = domain

    try:
        resp = requests.post(
            "https://api-ssl.bitly.com/v4/shorten",
            headers=headers,
            json=payload,
            timeout=10,
        )

        if resp.status_code not in (200, 201):
            return None, f"Bitly error {resp.status_code}: {resp.text}"

        data = resp.json()
        return data.get("link"), None

    except Exception as e:
        return None, str(e)


def update_bitly_title(bitlink: str, title: str) -> Optional[str]:
    """Step 2: Update Bitly title via PATCH."""
    token = st.secrets["BITLY_TOKEN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {"title": title}

    bitlink_id = bitlink.replace("https://", "")

    try:
        resp = requests.patch(
            f"https://api-ssl.bitly.com/v4/bitlinks/{bitlink_id}",
            headers=headers,
            json=payload,
            timeout=10,
        )

        if resp.status_code not in (200, 201):
            return f"Title update error {resp.status_code}: {resp.text}"

        return None

    except Exception as e:
        return f"Exception while setting title: {e}"


# ------------------------------------------------------------------
#                         UI RENDER
# ------------------------------------------------------------------

def render():
    st.header("UTM + Bitly Shortener")

    st.markdown("### Base URLs (one per line)")
    urls_input = st.text_area(
        "Paste URLs:",
        placeholder="https://site.com/page1\nhttps://site.com/page2",
        height=180
    )

    col1, col2 = st.columns(2)
    with col1:
        utm_source = st.text_input("utm_source")
        utm_medium = st.text_input("utm_medium")
    with col2:
        utm_campaign = st.text_input("utm_campaign")
        utm_term = st.text_input("utm_term (optional)")

    with st.expander("Bitly settings (optional)"):
        bitly_domain = st.text_input(
            "Bitly domain",
            value="bit.ly",
            help="For branded domains, replace with your domain."
        )

    if st.button("Process URLs"):
        urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
        if not urls:
            st.warning("Please paste URLs.")
            return

        results = []
        progress = st.progress(0)

        for i, url in enumerate(urls):
            # --------------------------------------------
            # Determine human-readable name from URL
            # --------------------------------------------
            parsed = urlparse(url)
            slug = parsed.path.strip("/").split("/")[0].replace("-", " ").title()
            readable_name = f"Розробка Shopify-магазину" if i == 0 else slug or parsed.netloc

            # --------------------------------------------
            # Build UTM
            # --------------------------------------------
            utm_url = build_utm_url(
                base_url=url,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_term=utm_term,
            )

            # --------------------------------------------
            # Shorten
            # --------------------------------------------
            short_url, err = shorten_with_bitly(utm_url, domain=bitly_domain or None)

            title_err = ""
            if short_url:
                final_title = f"{readable_name} — {utm_campaign}"
                title_err = update_bitly_title(short_url, final_title) or ""

            results.append({
                "Original URL": url,
                "UTM URL": utm_url,
                "Short URL": short_url if short_url else "",
                "Error": err or title_err,
            })

            progress.progress((i + 1) / len(urls))

        df = pd.DataFrame(results)

        st.success("Done!")

        # -----------------------------------------------------
        # Table
        # -----------------------------------------------------
        st.dataframe(df, use_container_width=True)

        # -----------------------------------------------------
        # Ready-to-copy formatted block
        # -----------------------------------------------------
        # ---------- Hardcoded Final Output Block ----------
        st.markdown("### 📌 Ready-to-copy formatted output")

        HARDCODED_LABELS = [
            "📌 Розробка Shopify-магазину для дропшипінгу «під ключ»",
            "📌 Індивідуальна розробка Shopify-магазину для вашого бренду",
            "📌 Підключення Shopify Payments, PayPal, Stripe",
            "📌 Рекламні креативи для тесту продукту",
            "📌 Особистий агент з Китаю",
            "📌 Voodoo Product Hunter — 15 потенційних winner-товарів кожного місяця"
        ]

        final_output_lines = []
        for label, row in zip(HARDCODED_LABELS, results):
            short = row["Short URL"]
            final_output_lines.append(f"{label} - {short}")

        st.code("\n".join(final_output_lines), language="text")

        # -----------------------------------------------------
        # CSV Download
        # -----------------------------------------------------
        st.download_button(
            "Download results as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="utm_bitly_results.csv",
            mime="text/csv"
        )
