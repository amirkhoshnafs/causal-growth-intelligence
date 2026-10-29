# Deployment and portfolio presentation

## Hugging Face Space

**Live application:** https://huggingface.co/spaces/amirkhoshnafs/causal-campaign-analyst-agent

The `app.py` bundled here comes from the author's supplied application, with one compatibility change to the timestamp annotation on the revenue chart. We could not independently verify the hosted Space's current commit. To keep GitHub and the public demo synchronized, update the Space source with this version and make sure it has the same requirements.

The Space typically needs a `README.md` containing Hugging Face YAML metadata (such as `sdk: streamlit` when supported by the current platform) and its own platform-specific configuration. **Do not overwrite the current Space README blindly**. Follow Hugging Face's current Space configuration guidance and commit the updated files through its repository interface.

## Smoke test after publishing

1. Open the demo in an incognito window.
2. Select **positive demo** and verify that the revenue chart, comparison chart, and decision card render.
3. Select **negative demo** and verify that a negative directional signal produces a pause/revise recommendation.
4. Upload one sample CSV and check formula trace, caveat warnings, and sensitivity table.
5. Verify the public PDF link and GitHub README images.

## Portfolio publishing note

The PDF included in `docs/` is a **redacted public distribution copy**, with named program affiliation and the specific video-demo links removed. Original source material remains untouched. There is no video embedded or required for this repository.
