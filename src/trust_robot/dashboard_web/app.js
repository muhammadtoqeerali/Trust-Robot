const SNAPSHOT_ENDPOINT = "/api/v1/snapshot";
const LIVE_EVENTS_ENDPOINT = "/api/v1/events";

let lastTransportUpdateAt = null;
let eventSource = null;

const VIEW_TITLES = {
  overview: "Overview",
  dataset: "Dataset & Replay",
  features: "Feature Signals",
  operations: "Sensor Operations",
  evidence: "Evidence Registry",
  health: "Health & Boundaries",
};

const byId = (id) => document.getElementById(id);

const setText = (id, value) => {
  const element = byId(id);

  if (element) {
    element.textContent = String(value);
  }
};

const yesNo = (value) => (value ? "Yes" : "No");

const openClosed = (value) => (value ? "Open" : "Closed");

const allowedBlocked = (value) => (value ? "Allowed" : "Blocked");

const formatMode = (value) =>
  String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());

const formatNumber = (value) => {
  if (typeof value !== "number") {
    return String(value);
  }

  if (Number.isInteger(value)) {
    return String(value);
  }

  return value.toPrecision(8).replace(/0+$/, "").replace(/\.$/, "");
};

const renderFeatureRows = (containerId, names, values) => {
  const container = byId(containerId);

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  names.forEach((name, index) => {
    const row = document.createElement("div");
    row.className = "feature-value-row";

    const label = document.createElement("span");
    label.textContent = name;

    const value = document.createElement("strong");
    value.textContent = formatNumber(values[index]);

    row.append(label, value);
    fragment.append(row);
  });

  container.replaceChildren(fragment);
};

const renderVelodyne = (containerId, payload) => {
  const container = byId(containerId);

  if (!container) {
    return;
  }

  const records = [
    ["serialized_payload_bytes", payload.serialized_payload_bytes],
    ["full_registration_rerun", payload.full_lidar_registration_rerun],
    ["contract_features", payload.frozen_SE3_lidar_feature_contract.length],
  ];

  const fragment = document.createDocumentFragment();

  records.forEach(([name, rawValue]) => {
    const row = document.createElement("div");
    row.className = "feature-value-row";

    const label = document.createElement("span");
    label.textContent = name;

    const value = document.createElement("strong");
    value.textContent =
      typeof rawValue === "boolean" ? yesNo(rawValue) : String(rawValue);

    row.append(label, value);
    fragment.append(row);
  });

  container.replaceChildren(fragment);
};

const renderExecutionFlow = (steps) => {
  const container = byId("execution-flow");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  steps.forEach((step, index) => {
    const item = document.createElement("li");

    const caption = document.createElement("small");
    caption.textContent = `Step ${index + 1}`;

    const label = document.createElement("strong");
    label.textContent = step;

    item.append(caption, label);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const formatBytes = (bytes) => {
  if (typeof bytes !== "number" || bytes < 0) {
    return "Unavailable";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1000 && unitIndex < units.length - 1) {
    value /= 1000;
    unitIndex += 1;
  }

  return `${value.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
};

const renderTrajectoryList = (
  containerId,
  trajectories,
  representative,
  closed,
) => {
  const container = byId(containerId);

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  trajectories.forEach((trajectory) => {
    const chip = document.createElement("span");
    chip.className = "trajectory-chip";
    chip.textContent = trajectory;

    if (trajectory === representative) {
      chip.classList.add("is-representative");
      chip.title = "Representative software qualification trajectory";
    }

    if (closed) {
      chip.classList.add("is-closed");
      chip.title = "Partition remains closed by scientific policy";
    }

    fragment.append(chip);
  });

  container.replaceChildren(fragment);
};

const renderReplayStreams = (streamIds) => {
  const container = byId("replay-stream-list");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  streamIds.forEach((streamId, index) => {
    const item = document.createElement("div");
    item.className = "replay-stream-item";

    const number = document.createElement("span");
    number.className = "replay-stream-index";
    number.textContent = String(index + 1).padStart(2, "0");

    const stream = document.createElement("code");
    stream.textContent = streamId;
    stream.title = streamId;

    item.append(number, stream);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const appendFeatureMetadata = (containerId, records) => {
  const container = byId(containerId);

  if (!container) {
    return;
  }

  const metadata = document.createElement("div");
  metadata.className = "feature-metadata";

  records.forEach(([label, rawValue]) => {
    const item = document.createElement("div");
    item.className = "feature-meta-item";

    const caption = document.createElement("span");
    caption.textContent = label;

    const value = document.createElement("code");
    value.textContent = String(rawValue);
    value.title = String(rawValue);

    item.append(caption, value);
    metadata.append(item);
  });

  container.append(metadata);
};

const renderBindingFields = (binding) => {
  const container = byId("binding-field-grid");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  binding.required_fields.forEach((field) => {
    const item = document.createElement("div");
    item.className = "binding-field-item";

    const name = document.createElement("code");
    name.textContent = field;
    name.title = field;

    const state = document.createElement("span");
    state.textContent = "Unavailable";

    item.append(name, state);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const renderOperationsLifecycle = (lifecycle) => {
  const container = byId("operations-lifecycle");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  lifecycle.forEach((record, index) => {
    const item = document.createElement("li");
    item.className = "operations-lifecycle-item";

    const number = document.createElement("span");
    number.className = "lifecycle-index";
    number.textContent = String(index + 1).padStart(2, "0");

    const label = document.createElement("strong");
    label.textContent = record.display_name;

    const state = document.createElement("span");
    state.className = "lifecycle-state";
    state.textContent = formatMode(record.state);

    item.append(number, label, state);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const renderOperationsChannels = (channels) => {
  const body = byId("operations-channel-body");

  if (!body) {
    return;
  }

  const fragment = document.createDocumentFragment();

  channels.forEach((channel) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = channel.display_name;

    const protocolCell = document.createElement("td");
    protocolCell.textContent = channel.protocol;

    const purposeCell = document.createElement("td");
    purposeCell.textContent =
      channel.path
        ? `${channel.purpose} · ${channel.path}`
        : channel.purpose;

    const endpointCell = document.createElement("td");
    endpointCell.className = "channel-state--unavailable";
    endpointCell.textContent = channel.real_endpoint_available
      ? "Available"
      : "Unavailable";

    const executionCell = document.createElement("td");
    executionCell.className = "channel-state--not-executed";
    executionCell.textContent = formatMode(channel.execution_state);

    const evidenceCell = document.createElement("td");
    evidenceCell.className = "channel-state--unavailable";
    evidenceCell.textContent = channel.real_sensor_evidence_available
      ? "Available"
      : "Unavailable";

    row.append(
      nameCell,
      protocolCell,
      purposeCell,
      endpointCell,
      executionCell,
      evidenceCell,
    );

    fragment.append(row);
  });

  body.replaceChildren(fragment);
};

const renderReceiptRegistry = (receipts) => {
  const container = byId("receipt-registry");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  receipts.forEach((receipt) => {
    const card = document.createElement("article");
    card.className = "receipt-card";

    if (receipt.synthetic) {
      card.classList.add("is-synthetic");
    }

    const heading = document.createElement("div");
    heading.className = "receipt-card-heading";

    const title = document.createElement("strong");
    title.textContent = receipt.display_name;

    const tag = document.createElement("span");
    tag.className = "receipt-tag";
    tag.textContent = receipt.synthetic ? "Synthetic" : "Software evidence";

    heading.append(title, tag);

    const hashes = document.createElement("div");
    hashes.className = "receipt-hash-list";

    const records = [];

    if (receipt.file_sha256) {
      records.push(["file sha256", receipt.file_sha256]);
    }

    if (receipt.content_sha256) {
      records.push(["content sha256", receipt.content_sha256]);
    }

    if (receipt.receipt_sha256) {
      records.push(["receipt sha256", receipt.receipt_sha256]);
    }

    records.push([
      "real sensor evidence",
      receipt.real_sensor_evidence ? "yes" : "no",
    ]);

    records.push([
      "run specific",
      receipt.run_specific ? "yes" : "no",
    ]);

    records.forEach(([labelText, valueText]) => {
      const item = document.createElement("div");
      item.className = "receipt-hash-item";

      const label = document.createElement("span");
      label.textContent = labelText;

      const value = document.createElement("code");
      value.textContent = valueText;
      value.title = valueText;

      item.append(label, value);
      hashes.append(item);
    });

    card.append(heading, hashes);
    fragment.append(card);
  });

  container.replaceChildren(fragment);
};

const renderHealthBlockers = (blockers) => {
  const container = byId("health-blocker-list");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  blockers.forEach((blocker, index) => {
    const item = document.createElement("div");
    item.className = "health-blocker-item";

    const number = document.createElement("span");
    number.className = "health-blocker-index";
    number.textContent = String(index + 1).padStart(2, "0");

    const label = document.createElement("strong");
    label.textContent = blocker.display_name;

    const state = document.createElement("span");
    state.className = "health-blocker-state";
    state.textContent = blocker.resolved ? "Resolved" : "Unresolved";

    item.append(number, label, state);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const renderSessionHistory = (history) => {
  const container = byId("session-history-list");

  if (!container) {
    return;
  }

  const fragment = document.createDocumentFragment();

  history.records.forEach((record, index) => {
    const item = document.createElement("div");
    item.className = "session-history-item";

    if (record.synthetic) {
      item.classList.add("is-synthetic");
    }

    const number = document.createElement("span");
    number.className = "history-index";
    number.textContent = String(index + 1).padStart(2, "0");

    const copy = document.createElement("div");
    copy.className = "history-copy";

    const title = document.createElement("strong");
    title.textContent = record.display_name;

    const metadata = document.createElement("span");
    metadata.textContent =
      `${record.evidence_class} · real sensor session: ${record.real_sensor_session ? "yes" : "no"}`;

    copy.append(title, metadata);

    const state = document.createElement("span");
    state.className = "history-state";
    state.textContent = formatMode(record.state);

    item.append(number, copy, state);
    fragment.append(item);
  });

  container.replaceChildren(fragment);
};

const setLiveChannelState = (state, label) => {
  const chip = byId("live-update-chip");

  if (!chip) {
    return;
  }

  chip.classList.remove(
    "is-live",
    "is-stale",
  );

  if (state === "live") {
    chip.classList.add("is-live");
  }

  if (state === "stale") {
    chip.classList.add("is-stale");
  }

  setText(
    "live-channel-state",
    label,
  );
};

const recordTransportUpdate = (observedAt) => {
  const parsed = Date.parse(
    observedAt
  );

  lastTransportUpdateAt = Number.isFinite(
    parsed
  )
    ? parsed
    : Date.now();

  setLiveChannelState(
    "live",
    "Live updates",
  );
};

const updateLastUpdateAge = () => {
  if (lastTransportUpdateAt === null) {
    setText(
      "last-update-age",
      "No update yet",
    );

    return;
  }

  const ageSeconds = Math.max(
    0,
    Math.floor(
      (
        Date.now()
        - lastTransportUpdateAt
      )
      / 1000
    ),
  );

  setText(
    "last-update-age",
    ageSeconds === 0
      ? "Updated now"
      : `Updated ${ageSeconds}s ago`,
  );

  if (ageSeconds > 20) {
    setLiveChannelState(
      "stale",
      "Update stale",
    );
  }
};

const renderEvidence = (sources) => {
  const body = byId("evidence-table-body");

  if (!body) {
    return;
  }

  const fragment = document.createDocumentFragment();

  sources.forEach((source) => {
    const row = document.createElement("tr");

    const pathCell = document.createElement("td");
    pathCell.textContent = source.path;

    const hashCell = document.createElement("td");
    const hash = document.createElement("code");
    hash.textContent = source.sha256;
    hash.title = source.sha256;
    hashCell.append(hash);

    const stateCell = document.createElement("td");
    stateCell.className = "evidence-state";
    stateCell.textContent = source.exists ? "Verified" : "Missing";

    row.append(pathCell, hashCell, stateCell);
    fragment.append(row);
  });

  body.replaceChildren(fragment);
};

const renderSnapshot = (snapshot) => {
  const {
    overview,
    repository,
    dataset,
    replay,
    features,
    acquisition,
    operations,
    receipts,
    health_supervision: healthSupervision,
    session_history: sessionHistory,
    scientific_boundary: science,
    evidence,
  } = snapshot;

  setText("sidebar-mode", formatMode(overview.mode));
  setText("commit-short", repository.head.slice(0, 10));

  setText(
    "software-qualification",
    formatMode(overview.software_level_end_to_end_qualification),
  );
  setText("frontier-label", formatMode(overview.current_scientific_frontier));

  setText("metric-train", dataset.counts.TRAIN);
  setText("metric-streams", overview.real_stream_count);
  setText("metric-replay", overview.bounded_replay_message_count);
  setText("metric-labels", science.real_health_label_count);

  setText("signal-sensor-contact", yesNo(acquisition.real_sensor_contact));
  setText("signal-runtime-bindings", acquisition.real_runtime_binding_count);
  setText(
    "signal-grounded-auth",
    acquisition.grounded_authorization_record_count,
  );
  setText(
    "signal-synthetic",
    acquisition.synthetic_live_stack.qualified ? "Qualified" : "Unavailable",
  );

  setText("sensor-badge", formatMode(acquisition.real_sensor_connection_state));
  setText("replay-digest", overview.bounded_replay_digest_sha256);

  setText("dataset-train-count", dataset.counts.TRAIN);
  setText("dataset-validation-count", dataset.counts.VALIDATION);
  setText("dataset-confirmation-count", dataset.counts.CONFIRMATION);
  setText("trajectory-name", overview.representative_real_data_trajectory);
  setText("dataset-deterministic", yesNo(overview.bounded_replay_deterministic));
  setText("dataset-message-count", overview.bounded_replay_message_count);
  setText("dataset-stream-count", overview.real_stream_count);
  setText("dataset-bag-size", formatBytes(replay.bag_file_size_bytes));

  setText("train-list-count", dataset.counts.TRAIN);
  setText("validation-list-count", dataset.counts.VALIDATION);
  setText("confirmation-list-count", dataset.counts.CONFIRMATION);

  renderTrajectoryList(
    "train-trajectory-list",
    dataset.trajectories.TRAIN,
    replay.trajectory_id,
    false,
  );

  renderTrajectoryList(
    "validation-trajectory-list",
    dataset.trajectories.VALIDATION,
    replay.trajectory_id,
    true,
  );

  renderTrajectoryList(
    "confirmation-trajectory-list",
    dataset.trajectories.CONFIRMATION,
    replay.trajectory_id,
    true,
  );

  renderReplayStreams(replay.real_stream_ids);
  setText("replay-bag-path", replay.bag_relative_path);

  setText("validation-lock", openClosed(dataset.validation_open));
  setText("confirmation-lock", openClosed(dataset.confirmation_open));

  renderFeatureRows(
    "camera-feature-values",
    features.camera.feature_names,
    features.camera.feature_values,
  );
  renderFeatureRows(
    "d435i-feature-values",
    features.d435i_imu.feature_names,
    features.d435i_imu.feature_values,
  );
  renderFeatureRows(
    "handsfree-feature-values",
    features.handsfree_imu.feature_names,
    features.handsfree_imu.feature_values,
  );
  renderVelodyne("velodyne-feature-values", features.velodyne);

  appendFeatureMetadata(
    "camera-feature-values",
    [
      ["bag timestamp ns", features.camera.bag_timestamp_ns],
      ["evidence class", features.evidence_class],
    ],
  );

  appendFeatureMetadata(
    "d435i-feature-values",
    [
      ["bag timestamp ns", features.d435i_imu.bag_timestamp_ns],
      ["trajectory", features.representative_trajectory],
    ],
  );

  appendFeatureMetadata(
    "handsfree-feature-values",
    [
      ["bag timestamp ns", features.handsfree_imu.bag_timestamp_ns],
      ["trajectory", features.representative_trajectory],
    ],
  );

  appendFeatureMetadata(
    "velodyne-feature-values",
    [
      ["bag timestamp ns", features.velodyne.bag_timestamp_ns],
      ["payload sha256", features.velodyne.serialized_payload_sha256],
    ],
  );

  setText(
    "operations-real-state",
    formatMode(operations.real_sensor_connection_state),
  );

  setText(
    "operations-binding-readiness",
    `${operations.runtime_binding.real_bound_field_count} / ${operations.runtime_binding.required_field_count}`,
  );

  setText(
    "operations-auth-count",
    operations.authorization.real_execution_authorization_count,
  );

  setText(
    "operations-grounded-auth-count",
    operations.authorization.grounded_authorization_record_count,
  );

  setText(
    "operations-session-state",
    operations.session.real_session_started ? "Started" : "Not started",
  );

  setText(
    "operations-session-id",
    operations.session.real_session_id === null
      ? "ID unavailable"
      : operations.session.real_session_id,
  );

  renderBindingFields(operations.runtime_binding);
  renderOperationsLifecycle(operations.lifecycle);
  renderOperationsChannels(operations.channels);

  renderExecutionFlow(
    operations.synthetic_qualification.execution_order,
  );

  setText(
    "synthetic-udp-receipt",
    yesNo(operations.synthetic_qualification.UDP_receipt_produced),
  );

  setText(
    "synthetic-identity-receipt",
    yesNo(operations.synthetic_qualification.identity_receipt_produced),
  );

  setText(
    "synthetic-status-receipt",
    yesNo(operations.synthetic_qualification.status_receipt_produced),
  );

  setText(
    "synthetic-diagnostic-receipt",
    yesNo(operations.synthetic_qualification.diagnostic_receipt_produced),
  );

  setText(
    "synthetic-composite-receipt",
    yesNo(operations.synthetic_qualification.composite_receipt_produced),
  );

  setText(
    "permission-real-execution",
    operations.controls.execute_real_sensor ? "Enabled" : "Disabled",
  );

  setText(
    "permission-binding-edit",
    operations.controls.edit_runtime_binding ? "Enabled" : "Disabled",
  );

  setText(
    "permission-create-auth",
    operations.controls.create_authorization ? "Enabled" : "Disabled",
  );

  setText(
    "permission-health-label",
    operations.controls.create_health_label ? "Enabled" : "Disabled",
  );

  setText(
    "permission-science-write",
    operations.controls.modify_scientific_parameters ? "Enabled" : "Disabled",
  );

  setText(
    "operations-network",
    operations.real_network_IO_executed ? "Executed" : "Not executed",
  );

  setText(
    "operations-contact",
    operations.real_sensor_contact ? "Contacted" : "Not contacted",
  );

  setText(
    "operations-auth",
    operations.authorization.grounded_authorization_record_count > 0
      ? "Present"
      : "Absent",
  );

  setText(
    "history-count-badge",
    `${sessionHistory.record_count} records`,
  );

  setText(
    "real-session-history-count",
    sessionHistory.real_sensor_session_count,
  );

  renderSessionHistory(
    sessionHistory,
  );

  setText(
    "repo-branch",
    repository.branch ?? "Unavailable",
  );

  setText(
    "repo-head",
    repository.head ?? "Unavailable",
  );

  setText(
    "repo-tree",
    repository.tree ?? "Unavailable",
  );

  setText(
    "repo-clean",
    repository.worktree_clean === true
      ? "Clean"
      : repository.worktree_clean === false
        ? "Modified"
        : "Unavailable",
  );

  setText(
    "receipt-count-badge",
    `${receipts.receipt_count} receipts`,
  );

  renderReceiptRegistry(
    receipts.registry,
  );

  renderEvidence(evidence.sources);

  setText(
    "health-readiness-state",
    healthSupervision.training_ready ? "Ready" : "Blocked",
  );

  setText(
    "health-unresolved-count",
    healthSupervision.unresolved_blocker_count,
  );

  renderHealthBlockers(
    healthSupervision.blockers,
  );

  setText(
    "boundary-baseline-sources",
    healthSupervision.accepted_baseline_nominality_source_count,
  );

  setText(
    "boundary-supervision",
    science.accepted_health_supervision_source_count,
  );
  setText(
    "boundary-labels",
    healthSupervision.real_health_label_count,
  );

  setText(
    "boundary-bindings",
    science.real_runtime_binding_count,
  );

  setText(
    "health-policy-labels",
    healthSupervision.feature_values_may_be_used_as_health_labels
      ? "Allowed"
      : "Forbidden",
  );

  setText(
    "health-policy-predictions",
    healthSupervision.feature_values_may_be_used_as_health_predictions
      ? "Allowed"
      : "Forbidden",
  );

  setText(
    "health-control-create-label",
    healthSupervision.dashboard_controls.create_health_label
      ? "Enabled"
      : "Disabled",
  );

  setText(
    "health-control-authorize-training",
    healthSupervision.dashboard_controls.authorize_training
      ? "Enabled"
      : "Disabled",
  );

  setText(
    "health-control-override",
    healthSupervision.dashboard_controls.override_blocker
      ? "Enabled"
      : "Disabled",
  );

  setText(
    "gate-se2-training",
    healthSupervision.SE2_health_model_training_blocked
      ? "Blocked"
      : "Allowed",
  );

  setText("gate-se4-complete", yesNo(science.SE4_complete));
  setText(
    "gate-se4-training",
    science.SE4_training_execution_blocked ? "Blocked" : "Allowed",
  );
  setText("gate-se5", science.SE5_entry_blocked ? "Blocked" : "Allowed");

  setText(
    "gate-interval-binding",
    healthSupervision.interval_binding_established
      ? "Established"
      : "Unavailable",
  );

  setText(
    "gate-measurement-time",
    healthSupervision.physical_measurement_time_established
      ? "Established"
      : "Unavailable",
  );

  setText(
    "gate-ate",
    science.ATE_RPE_computed ? "Computed" : "Unavailable",
  );

  const connection = byId("connection-state");

  if (connection) {
    connection.classList.remove("is-error");
    connection.classList.add("is-online");
    connection.lastElementChild.textContent = "Local API online";
  }
};

const showError = (message) => {
  const alert = byId("dashboard-alert");

  if (alert) {
    alert.textContent =
      `Dashboard state unavailable. ${message} No fallback scientific values were invented.`;
    alert.classList.remove("is-hidden");
  }

  const connection = byId("connection-state");

  if (connection) {
    connection.classList.remove("is-online");
    connection.classList.add("is-error");
    connection.lastElementChild.textContent = "API unavailable";
  }
};

const activateView = (viewName) => {
  const safeView = Object.hasOwn(VIEW_TITLES, viewName) ? viewName : "overview";

  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.panel === safeView);
  });

  document.querySelectorAll("[data-view]").forEach((link) => {
    const active = link.dataset.view === safeView;
    link.classList.toggle("is-active", active);

    if (active) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });

  setText("page-title", VIEW_TITLES[safeView]);
  document.body.classList.remove("nav-open");

  const menuButton = byId("mobile-menu-button");

  if (menuButton) {
    menuButton.setAttribute("aria-expanded", "false");
  }
};

const bindNavigation = () => {
  document.querySelectorAll("[data-view]").forEach((link) => {
    link.addEventListener("click", () => {
      activateView(link.dataset.view);
    });
  });

  window.addEventListener("hashchange", () => {
    activateView(window.location.hash.replace("#", ""));
  });

  const menuButton = byId("mobile-menu-button");

  if (menuButton) {
    menuButton.addEventListener("click", () => {
      const open = document.body.classList.toggle("nav-open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
  }

  activateView(window.location.hash.replace("#", ""));
};

const applySnapshot = (
  snapshot,
  transportObservedAt = new Date().toISOString(),
) => {
  if (snapshot.read_only !== true) {
    throw new Error("API did not report read-only mode");
  }

  renderSnapshot(
    snapshot
  );

  recordTransportUpdate(
    transportObservedAt
  );

  const alert = byId("dashboard-alert");

  if (alert) {
    alert.classList.add("is-hidden");
    alert.textContent = "";
  }
};

const loadSnapshot = async () => {
  const refreshButton = byId("refresh-button");

  if (refreshButton) {
    refreshButton.disabled = true;
  }

  try {
    const response = await fetch(SNAPSHOT_ENDPOINT, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const snapshot = await response.json();

    applySnapshot(
      snapshot,
      new Date().toISOString(),
    );
  } catch (error) {
    showError(
      error instanceof Error
        ? error.message
        : "Unknown API error"
    );
  } finally {
    if (refreshButton) {
      refreshButton.disabled = false;
    }
  }
};

const connectLiveUpdates = () => {
  if (!("EventSource" in window)) {
    setLiveChannelState(
      "stale",
      "Live updates unsupported",
    );

    return;
  }

  eventSource = new EventSource(
    LIVE_EVENTS_ENDPOINT,
    {
      withCredentials: true,
    },
  );

  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(
        event.data
      );

      if (
        payload.schema
        !== "TRUST_ROBOT_DASHBOARD_LIVE_EVENT_V1"
      ) {
        throw new Error(
          "Unexpected live-event schema"
        );
      }

      if (
        payload.transport_time_is_sensor_measurement_time
        !== false
      ) {
        throw new Error(
          "Transport timestamp boundary violated"
        );
      }

      applySnapshot(
        payload.snapshot,
        payload.transport_observed_at_utc,
      );
    } catch (error) {
      setLiveChannelState(
        "stale",
        "Live event rejected",
      );
    }
  };

  eventSource.onerror = () => {
    setLiveChannelState(
      "idle",
      "Reconnecting",
    );
  };
};

const bindRefresh = () => {
  const refreshButton = byId(
    "refresh-button"
  );

  if (!refreshButton) {
    return;
  }

  refreshButton.addEventListener(
    "click",
    () => {
      loadSnapshot();
    },
  );
};

window.addEventListener(
  "beforeunload",
  () => {
    if (eventSource) {
      eventSource.close();
    }
  },
);

bindNavigation();
bindRefresh();
loadSnapshot();
connectLiveUpdates();
setInterval(
  updateLastUpdateAge,
  1000,
);
