"""Main Streamlit entry point for AstroScope AI."""

import streamlit as st

from astroscope.exoplanet_dashboard import render_exoplanet_dashboard
from astroscope.gaia_dashboard import render_gaia_dashboard
from astroscope.i18n import SUPPORTED_LANGUAGES
from astroscope.light_curve_dashboard import render_light_curve_dashboard
from astroscope.observatory_dashboard import render_observatory_dashboard
from astroscope.transit_schedule_dashboard import render_transit_schedule_dashboard

st.set_page_config(
    page_title="AstroScope AI Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def select_language() -> str:
    """Render the shared language selector and return its language code."""

    language_name = st.sidebar.selectbox(
        "Language / 言語 / 언어 / ภาษา",
        options=list(SUPPORTED_LANGUAGES),
    )

    return SUPPORTED_LANGUAGES[language_name]


def render_observatory_page() -> None:
    language = select_language()
    render_observatory_dashboard(language)


def render_light_curve_page() -> None:
    """Render the standalone astronomical light-curve laboratory."""

    language = select_language()
    render_light_curve_dashboard(language)


def render_gaia_page() -> None:
    """Render the standalone Gaia DR3 catalogue explorer."""

    language = select_language()
    render_gaia_dashboard(language)


def render_exoplanet_page() -> None:
    """Render the standalone NASA exoplanet explorer."""

    language = select_language()
    render_exoplanet_dashboard(language)


def render_transit_schedule_page() -> None:
    """Render the standalone exoplanet transit scheduler."""

    language = select_language()
    render_transit_schedule_dashboard(language)


def run_app() -> None:
    """Run the AstroScope multipage application."""

    navigation = st.navigation(
        [
            st.Page(
                render_observatory_page,
                title="Observatory",
                icon="🔭",
                default=True,
            ),
            st.Page(
                render_light_curve_page,
                title="Light Curve Laboratory",
                icon="📈",
            ),
            st.Page(
                render_gaia_page,
                title="Gaia DR3 Explorer",
                icon="🛰️",
            ),
            st.Page(
                render_exoplanet_page,
                title="Exoplanet Explorer",
                icon="🪐",
            ),
            st.Page(
                render_transit_schedule_page,
                title="Transit Schedule",
                icon="🗓️",
            ),
        ]
    )
    navigation.run()


if __name__ == "__main__":
    run_app()
