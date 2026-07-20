"""Main Streamlit entry point for AstroScope AI."""

import streamlit as st

from astroscope.i18n import SUPPORTED_LANGUAGES, translate

st.set_page_config(
    page_title="AstroScope AI Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

language_name = st.sidebar.selectbox(
    "Language / 言語 / 언어 / ภาษา",
    options=list(SUPPORTED_LANGUAGES),
)

language = SUPPORTED_LANGUAGES[language_name]

st.title(f"🔭 {translate('app_title', language)}")
st.subheader(translate("app_subtitle", language))

st.success(translate("foundation_message", language))
st.write(translate("welcome", language))

st.markdown(f"## {translate('future_features', language)}")

st.markdown(
    "\n".join(
        [
            f"- {translate('feature_visibility', language)}",
            f"- {translate('feature_planetarium', language)}",
            f"- {translate('feature_telescope', language)}",
        ]
    )
)