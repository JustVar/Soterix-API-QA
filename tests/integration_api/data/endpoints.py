"""Endpoint catalogue for the /v-integration-api surface.

One row per endpoint in the live spec (/v-integration-api/v3/api-docs,
14 paths as of 2026-08-27). The Swagger UI is the source of truth and grows
over time: when it gains a path, add a row here and the sweep picks it up.

Each row: (name, path_template, kind)

Path templates use placeholders resolved live by the `integration_ids`
fixture: {siteid} {channelid} {starttimestamp}.

`kind` names the response contract we verified against the live surface,
because a bare "200 + JSON" check gets this surface wrong:

  data          200, body.result is a non-empty list of objects
  data_any      200, body.result is a list that may be validly empty
                (per-camera parameter listings after tenant data churn)
  pointer       200, no code/result envelope. body.message says to use a
                portal link and body.streamingServerUrl carries the portal
                URL (live-event / streaming)
  session       200, body.message "Successfully Updated!"
  stream_start  200, body.message "Successfully created!" and body.result[0]
                carries a streamurl (calling it creates a server-side
                streaming session, like the product UI does)
  no_data       needs an id we cannot discover (snapid). A guessed id gets
                400 "check your request parameters", so the sweep only
                asserts the auth layer passes
"""

GET_ENDPOINTS = [
    # --- Sites ---
    ("site_list", "/REST/site", "data"),
    ("site_by_id", "/REST/site/{siteid}", "data"),

    # --- Cameras ---
    ("channel_list_all_sites", "/REST/site/channel", "data"),
    ("channel_list_by_site", "/REST/site/channel/{siteid}", "data"),
    ("channel_by_id", "/REST/site/channel/{siteid}/{channelid}", "data"),
    ("channel_streaming_parameter",
     "/REST/site/channel/{siteid}/{channelid}/streaming/parameter",
     "data_any"),
    ("channel_streaming_capability",
     "/REST/site/channel/{siteid}/{channelid}/streaming/parameter/capability",
     "data_any"),
    ("channel_image_parameter",
     "/REST/site/channel/{siteid}/{channelid}/image/parameter", "data_any"),

    # --- Events ---
    ("event_portal_pointer", "/REST/event", "pointer"),
    ("event_snap", "/REST/event/snap/{siteid}/1", "no_data"),

    # --- Streaming ---
    ("stream_portal_pointer", "/REST/stream", "pointer"),
    ("stream_session", "/REST/stream/session", "session"),
    ("stream_start_live",
     "/REST/stream/{siteid}/startlive/{channelid}", "stream_start"),
    ("stream_start_archive",
     "/REST/stream/{siteid}/startarchive/{channelid}/{starttimestamp}",
     "stream_start"),
]
