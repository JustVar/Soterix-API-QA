"""
GET-endpoint catalogue for the smoke suite, kept separate from test logic
so other suites (contract, functional) can reuse the same endpoint list
without importing test code.

(readable_name, path_template) - path templates use the SAME placeholder
names as conftest.discovery_context keys: {siteid} {enterpriseid}
{channelid} {userid} {profileid} {starttimestamp} {endtimestamp}
"""

GET_ENDPOINTS = [
    # --- site-controller-impl -------------------------------------------
    ("get_site", "/REST/site/{siteid}"),
    ("get_site_all", "/REST/site"),
    ("get_site_count", "/REST/site/count"),
    ("get_site_details", "/REST/site/{siteid}/getsitedetails"),
    ("get_site_heartbeat", "/REST/site/{siteid}/heartbeat"),
    ("get_site_license", "/REST/site/{siteid}/license"),
    ("get_site_location", "/REST/site/{siteid}/location"),
    ("get_site_login_sessions", "/REST/site/{siteid}/getloginsessions"),
    ("get_site_user", "/REST/site/{siteid}/user"),
    ("get_site_userprofile", "/REST/site/{siteid}/userprofile"),
    ("get_site_all_groups", "/REST/site/{siteid}/getAllGroups"),
    ("get_site_all_junctions", "/REST/site/{siteid}/getAllJunctions"),
    ("get_site_installation_type", "/REST/site/{siteid}/installationtype"),
    ("get_site_rcsagents", "/REST/site/rcsagents"),
    ("get_site_recordingstream", "/REST/site/recordingstream"),
    ("get_site_nonenterprise", "/REST/site/nonenterprise"),
    ("get_site_grouptree", "/REST/site/{siteid}/grouptree"),
    ("get_site_locationtree", "/REST/site/{siteid}/locationtree"),
    ("get_site_junctiontree", "/REST/site/{siteid}/junction/tree"),

    # --- site-channel-controller-impl ------------------------------------
    ("get_channel_list", "/REST/site/{siteid}/channel"),
    ("get_all_channel", "/REST/site/{siteid}/allchannel"),
    ("get_channel_by_id", "/REST/site/{siteid}/channel/{channelid}"),
    ("get_channel_status_all", "/REST/site/{siteid}/channel/status"),
    ("get_channel_count", "/REST/site/{siteid}/channel/count"),
    ("get_channel_model", "/REST/site/{siteid}/channel/model"),
    ("get_channel_withsnap", "/REST/site/{siteid}/channel/withsnap"),
    ("get_channel_config", "/REST/site/{siteid}/channel/{channelid}/config"),
    ("get_channel_privacyzone", "/REST/site/{siteid}/channel/{channelid}/getprivacyzone"),

    # --- site-analytics-controller-impl -----------------------------------
    ("get_analytic_jobs", "/REST/site/{siteid}/analytic"),
    ("get_analytic_servers", "/REST/site/{siteid}/analyticserver"),
    ("get_analytic_type", "/REST/site/{siteid}/analytic/type"),
    ("get_analytic_filter", "/REST/site/{siteid}/analytic/filter"),
    ("get_analytic_by_channel", "/REST/site/{siteid}/analytic/channel/{channelid}"),

    # --- site-analytics-type-controller-impl --------------------------------
    ("get_analytics_types", "/REST/site/analyticstype"),
    ("get_analytics_all", "/REST/site/analytics"),
    ("get_enterprise_analytics", "/REST/site/analytics/enterprise"),

    # --- site-vms-config-controller-impl -----------------------------------
    ("get_all_users_on_site", "/REST/site/{siteid}/users"),
    ("get_current_media_servers", "/REST/site/{siteid}/currentmediaservers"),
    ("get_media_servers", "/REST/site/{siteid}/mediaserver"),
    ("get_current_vms_storages", "/REST/site/{siteid}/storage/current"),
    ("get_available_vms_storages", "/REST/site/{siteid}/storage/available"),
    ("get_gis_map_config", "/REST/site/{siteid}/gismapconfig"),
    ("get_all_privacy_zone", "/REST/site/{siteid}/privacyzone"),
    ("get_all_user_profiles", "/REST/site/{siteid}/alluserprofiles"),
    ("get_edge_activated_channels", "/REST/site/{siteid}/edgeactivechannels"),

    # --- site-scheduler-controller-impl -------------------------------------
    ("get_site_recording_schedule", "/REST/site/{siteid}/recordingschedule"),
    ("get_special_days", "/REST/site/{siteid}/getspecialdays"),

    # --- site-event-controller-impl ------------------------------------------
    ("get_analytic_events", "/REST/site/{siteid}/event/{startts}/{endts}"),
    ("get_events_by_channel", "/REST/site/{siteid}/event/channel/{channelid}"),
    ("get_assigned_ptz_autotour_to_event", "/REST/site/{siteid}/getassignedptzautotourtoevent"),

    # --- dashboard-controller-impl --------------------------------------------
    ("get_my_dashboards", "/REST/dashboard/getmydashboards"),
    ("get_all_dashboards", "/REST/dashboard/getalldashboards"),
    ("get_all_widgets", "/REST/dashboard/widget/getallwidgets"),
    ("get_my_widgets", "/REST/dashboard/widget/mywidgets"),

    # --- admin-dashboard-controller-impl ---------------------------------------
    ("get_dashboard_counts", "/REST/dashboard/count"),
    ("get_site_status_dashboard", "/REST/dashboard/site/{siteid}/status"),

    # --- customer / enterprise --------------------------------------------------
    ("get_enterprise", "/REST/enterprise/{enterpriseid}"),
    ("get_enterprise_all", "/REST/enterprise"),
    ("get_enterprise_count", "/REST/enterprise/count"),
    ("get_enterprise_name", "/REST/enterprise/name"),
    ("get_sites_under_enterprise", "/REST/enterprise/{enterpriseid}/site"),
    ("get_operators_under_enterprise", "/REST/enterprise/{enterpriseid}/user"),
    ("get_all_users_under_enterprise", "/REST/enterprise/{enterpriseid}/alluser"),
    ("get_all_customers", "/REST/customer"),
    ("get_customer_overview", "/REST/customer/overview"),
    ("get_customer_by_id", "/REST/customer/{enterpriseid}"),
    ("get_site_by_enterprise_customer", "/REST/customer/site/enterpriseid/{enterpriseid}"),

    # --- central-user-controller-impl --------------------------------------------
    ("get_central_admins", "/REST/central/user/admin"),
    ("get_central_operators", "/REST/central/user/operator"),
    ("get_central_enterprise_users", "/REST/central/user/enterprise/{enterpriseid}"),
    ("get_central_user_session", "/REST/central/user/session"),
    ("get_central_user_catalogue", "/REST/central/user/catalogue"),

    # --- central-user-role/profile-controller-impl --------------------------------
    ("get_central_user_profile_roles", "/REST/central/userprofile/roles"),
    ("get_central_user_role", "/REST/central/role/{enterpriseid}"),

    # --- log ---------------------------------------------------------------------
    ("get_log_filters", "/REST/log/filters"),

    # --- plan / license ------------------------------------------------------------
    ("get_plan", "/REST/plan"),
    ("get_plan_by_enterprise", "/REST/plan/enterprise/{enterpriseid}"),
    ("get_platform_license", "/REST/platform/license"),
    ("get_enterprise_license", "/REST/enterprise/license/{enterpriseid}"),
    ("get_user_license_overview", "/REST/user/license/overview/{enterpriseid}"),

    # --- resource servers (storage/streaming/analytics) -----------------------------
    ("get_all_storage_servers", "/REST/resource/storage"),
    ("get_all_streaming_servers", "/REST/resource/streaming"),
    ("get_all_analytics_servers", "/REST/resource/analytics"),

    # --- media / clip bookmark -----------------------------------------------------
    ("get_clip_bookmarks", "/REST/clipbookmark"),
    ("get_vault_storage", "/REST/media/storage/vault"),

    # --- preset / favourites --------------------------------------------------------
    ("get_all_presets", "/REST/preset"),
    ("get_my_presets", "/REST/preset/mypresets"),
    ("get_all_favourites", "/REST/favourite/getallfavourites"),

    # --- camera sequence -------------------------------------------------------------
    ("get_camera_sequence", "/REST/camera/sequence"),

    # --- webhook -----------------------------------------------------------------------
    ("get_webhook_types", "/REST/webhook/type"),
    ("get_webhook_auth_types", "/REST/webhook/auth/type"),
    ("get_webhooks_by_enterprise", "/REST/webhook/{enterpriseid}"),

    # --- lpr -------------------------------------------------------------------------
    ("get_lpr_categories", "/REST/lpr/enterprise/{enterpriseid}/category"),
    ("get_lpr_customlist", "/REST/lpr/enterprise/{enterpriseid}/customlist"),
    ("get_lpr_channel_tree", "/REST/lpr/site/{siteid}/location/tree"),

    # --- edge version ------------------------------------------------------------------
    ("get_latest_edge_version", "/REST/edge/version/latest"),
    ("get_current_edge_version", "/REST/edge/version/site/{siteid}/current"),

    # --- application / system ------------------------------------------------------------
    ("get_application_version", "/REST/application/version"),
    ("get_system_configuration", "/REST/systemconfig"),

    # --- segment ---------------------------------------------------------------------------
    ("get_all_segment", "/REST/segment"),
    ("get_segment_by_enterprise", "/REST/segment/enterprise/{enterpriseid}"),
]

# ---------------------------------------------------------------------------
# Endpoints the sweep skips. Each row names an endpoint above and the reason
# the sweep skips it: the test account lacks the role, or the server does
# not serve the endpoint. These are NOT framework bugs. The API rejects the
# call on purpose. Kept here instead of deleted so the endpoint stays
# visible and one deleted line puts it back in the sweep.
#
# How to add one: put the endpoint name (the first field of its row above)
# and a one-line reason, measured on this server, in the dict below. The
# sweep calls pytest.skip(reason) for it. A skip is not a pass, so
# re-measure every row on a new server: delete the row, run the sweep, and
# keep the row only if the endpoint still fails for the stated reason.
# ---------------------------------------------------------------------------

# Every reason below was measured on the previous QA server. A new server
# does not inherit them silently: the prefix says so in the skip message.
_PREVIOUS = "measured on the previous QA server; re-measure here: "

# One shared reason for the endpoints that the server proxies to a site's
# recorder (VMS). Sites without a recorder answer 502 on all of them while
# /channel answers 200. On a server whose sites have a recorder, delete
# these rows.
VMS_502 = _PREVIOUS + ("502: the endpoint is proxied to the site's VMS backend, which the emulated sites do not serve. Measured on 2 sites outside pytest while /channel answered 200 on both.")

KNOWN_LIMITATIONS = {
    "get_site_nonenterprise": _PREVIOUS + "requires central/platform admin role (got 400: 'not allowed to perform this operation')",
    "get_site_by_enterprise_customer": _PREVIOUS + "requires central super admin role (got 400: 'not a super admin in the central server')",
    "get_all_streaming_servers": _PREVIOUS + "requires central super admin role (got 400: 'not a super admin in the central server')",
    "get_all_analytics_servers": _PREVIOUS + "requires 'partner' role in the central server (got 400: 'not a partner')",
    "get_application_version": _PREVIOUS + "404 'File not available or invalid installation' - endpoint not provisioned on that server",
    "get_all_privacy_zone": VMS_502,
    "get_all_user_profiles": VMS_502,
    "get_all_users_on_site": VMS_502,
    "get_analytic_by_channel": VMS_502,
    "get_analytic_events": VMS_502,
    "get_analytic_filter": VMS_502,
    "get_analytic_jobs": VMS_502,
    "get_analytic_servers": VMS_502,
    "get_analytic_type": VMS_502,
    "get_assigned_ptz_autotour_to_event": VMS_502,
    "get_available_vms_storages": VMS_502,
    "get_channel_config": VMS_502,
    "get_channel_privacyzone": VMS_502,
    "get_channel_status_all": VMS_502,
    "get_current_media_servers": VMS_502,
    "get_current_vms_storages": VMS_502,
    "get_edge_activated_channels": VMS_502,
    "get_events_by_channel": VMS_502,
    "get_gis_map_config": VMS_502,
    "get_media_servers": VMS_502,
    "get_site_all_junctions": VMS_502,
    "get_site_heartbeat": VMS_502,
    "get_site_installation_type": VMS_502,
    "get_site_license": VMS_502,
    "get_site_login_sessions": VMS_502,
    "get_site_recording_schedule": VMS_502,
    "get_site_user": VMS_502,
    "get_site_userprofile": VMS_502,
    "get_special_days": VMS_502,
}
