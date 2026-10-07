"""Run with: streamlit run app.py"""
import time
import pandas as pd
import streamlit as st
from PIL import Image
from ocr import extract_text
from compare import compare_label
from warning import check_warning
from batch import overall, parse_applications, run_batch, to_csv, TEMPLATE

COLORS = {"Match": "#1a7f37", "Needs Review": "#b7791f", "Mismatch": "#c0392b", "Error": "#6b7280"}
ICONS = {"Match": "✅", "Needs Review": "⚠️", "Mismatch": "❌", "Error": "🚫"}

st.set_page_config(page_title="Label Check", layout="centered")
st.title("Label Check")
single_tab, batch_tab = st.tabs(["One label", "Many labels"])

# ---------- One label ----------
with single_tab:
    st.write("Enter what the application says, upload the label image, then press **Check label**.")
    with st.form("check"):
        brand = st.text_input("Brand name", "OLD TOM DISTILLERY")
        class_type = st.text_input("Class/type", "Kentucky Straight Bourbon Whiskey")
        c1, c2 = st.columns(2)
        abv = c1.text_input("Alcohol content", "45% Alc./Vol.")
        volume = c2.text_input("Net contents", "750 mL")
        upload = st.file_uploader("Label image", type=["png", "jpg", "jpeg"])
        go = st.form_submit_button("Check label", type="primary", use_container_width=True)

    if go:
        if not upload:
            st.error("Upload a label image first.")
        else:
            start = time.perf_counter()
            text = extract_text(Image.open(upload))
            results = compare_label(dict(brand=brand, class_type=class_type, abv=abv, volume=volume), text)
            w_status, w_msg = check_warning(text)
            elapsed = time.perf_counter() - start
            total = overall([r.status for r in results] + [w_status])
            st.markdown(f"<h2 style='color:{COLORS[total]}'>{ICONS[total]} {total}</h2>", unsafe_allow_html=True)
            st.caption(f"Checked in {elapsed:.1f} seconds" + ("" if elapsed <= 5 else " (slower than the 5 second goal)"))
            for r in results:
                st.markdown(f"{ICONS[r.status]} **{r.field}**: {r.status}")
                if r.note:
                    st.caption(r.note)
            st.markdown(f"{ICONS[w_status]} **Government warning**: {w_status}")
            st.caption(w_msg)
            with st.expander("Text read from the label"):
                st.text(text)

# ---------- Many labels ----------
with batch_tab:
    st.write("1. Download the template and fill in one row per label. The **filename** must match the image file name.")
    st.download_button("Download CSV template", TEMPLATE, "applications_template.csv", "text/csv")
    app_csv = st.file_uploader("2. Application data (CSV)", type=["csv"], key="csv")
    images = st.file_uploader("3. Label images", type=["png", "jpg", "jpeg"],
                              accept_multiple_files=True, key="imgs")
    run = st.button("Check all labels", type="primary", use_container_width=True)

    if run:
        if not app_csv or not images:
            st.error("Upload both the application CSV and at least one label image.")
        else:
            try:
                apps = parse_applications(app_csv.getvalue().decode("utf-8", errors="replace"))
            except Exception:
                apps = {}
            if not apps:
                st.error("Could not read the CSV. Use the template columns: filename, brand, class_type, abv, volume.")
            else:
                bar = st.progress(0.0, text="Starting...")
                start = time.perf_counter()
                st.session_state["rows"] = run_batch(
                    [(f.name, f.getvalue()) for f in images], apps,
                    on_progress=lambda i, n: bar.progress(i / n, text=f"Checked {i} of {n}"))
                st.session_state["secs"] = time.perf_counter() - start
                bar.empty()

    rows = st.session_state.get("rows")
    if rows:
        counts = {s: sum(r["Overall"] == s for r in rows) for s in COLORS}
        cols = st.columns(4)
        for col, (status, n) in zip(cols, counts.items()):
            col.metric(f"{ICONS[status]} {status}", n)
        st.caption(f"{len(rows)} labels in {st.session_state['secs']:.1f} seconds. Problems are listed first.")
        show = st.radio("Show", ["All", "Needs attention only"], horizontal=True)
        view = [r for r in rows if show == "All" or r["Overall"] != "Match"]
        df = pd.DataFrame(view).fillna("")
        paint = lambda v: f"color: {COLORS[v]}; font-weight: 600" if v in COLORS else ""
        styler = df.style.map(paint) if hasattr(df.style, "map") else df.style.applymap(paint)
        st.dataframe(styler, use_container_width=True, hide_index=True)
        st.download_button("Download results (CSV)", to_csv(rows), "label_results.csv", "text/csv",
                           use_container_width=True)
