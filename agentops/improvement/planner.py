# agentops/improvement/planner.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.aut_spec import AUTSpec
from core.common.change_set import ChangeSet, save_new_config
from agentops.travel_planner_planner import propose_travel_changeset


class PlannerEngine:
    """
    PlannerEngine proposes config changes + new tests for a given AUT version.

    For now this is wired *specifically* to the travel_planner ADK app by
    delegating to `agentops.travel_planner_planner.propose_travel_changeset`.

    Later, you can:
      - branch on aut_spec.aut_id
      - add generic planners for other ADK agents
    """

    def __init__(self, spec: AUTSpec):
        self.aut_spec = spec

    def _derive_new_config_path(self, base_config: str, version_id: str) -> str:
        """
        Derive a new config path from the base config.

        Example:
          base_config: "v2_adk/travel_planner/specs/travel_planner_config_v1.json"
          -> "v2_adk/travel_planner/specs/travel_planner_config_v2.json"

        If no clear pattern is found, we fall back to:
          "<stem>_<version_id>_improved.json"
        """
        path = Path(base_config)
        stem = path.stem  # e.g. "travel_planner_config_v1"
        suffix = path.suffix  # ".json"

        if stem.endswith("_v1"):
            new_stem = stem[:-3] + "_v2"
        else:
            new_stem = f"{stem}_{version_id}_improved"

        return str(path.with_name(new_stem + suffix))

    def propose_changeset(
        self,
        version_id: str,
        min_score: float = 4.0,
    ) -> ChangeSet:
        """
        Main entrypoint used by the Supervisor's `improve` command.

        Steps:
          1. Read the ADK config_file path from AUTSpec.adk.
          2. Derive a new config path for the improved version.
          3. Call `propose_travel_changeset` to ask Gemini for patches + new tests.
          4. Convert the raw dict into a ChangeSet instance.
          5. Apply patches to create and save the new config file.
          6. Return the ChangeSet for display / further use.
        """
        # 1) Get base config path from the AUT spec
        adk_cfg: dict[str, Any] | None = self.aut_spec.adk
        if not adk_cfg or "config_file" not in adk_cfg:
            raise ValueError(
                "PlannerEngine requires AUTSpec.adk['config_file'] "
                "to know which config to patch."
            )

        base_config_path = adk_cfg["config_file"]

        # 2) Derive new config path
        new_config_path = self._derive_new_config_path(
            base_config=base_config_path,
            version_id=version_id,
        )

        # 3) Call the travel-specific planner helper
        proposal_dict = propose_travel_changeset(
            base_config_path=base_config_path,
            new_config_path=new_config_path,
            version_id=version_id,
            min_score=min_score,
        )

        # 4) Normalize into ChangeSet
        changeset = ChangeSet.from_dict(proposal_dict)

        # 5) Persist the new config to disk
        save_new_config(
            base_path=changeset.base_config_path,
            new_path=changeset.new_config_path,
            patches=changeset.config_patches,
        )

        # 6) Return ChangeSet so Supervisor can pretty-print it
        return changeset
