"""Streamlit operator UI for the TCIN Impression Mapper.

This is an optional, internal-facing review tool — NOT part of the deployed
FastAPI service. It reads directly from MongoDB (sync PyMongo) via ai-mongo and
lets reviewers inspect and correct color → impression mappings.

Run it with:  make run-tcin-ui   (requires the `ui` dependency group)
"""
