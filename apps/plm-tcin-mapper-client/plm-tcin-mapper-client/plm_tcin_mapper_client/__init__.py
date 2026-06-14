"""Streamlit operator UI for the TCIN Impression Mapper.

This is an optional, internal-facing review tool — NOT part of the deployed
FastAPI service. It calls plm-tcin-mapper-api over HTTP and does not connect to
MongoDB or ThinkTank directly.

Run it with:  make run-tcin-ui   (requires the `ui` dependency group)
"""
