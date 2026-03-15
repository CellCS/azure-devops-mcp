# /app/devops_client.py

import html
import re
from typing import Any, Dict
from urllib.parse import quote

import requests
from defusedxml import ElementTree as DefusedET
from requests.auth import HTTPBasicAuth

from .config import get_settings


class AzureDevOpsClient:
    REQUEST_TIMEOUT_SECONDS = (5, 30)

    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"https://dev.azure.com/{self.settings.azure_org}"
        self.auth = HTTPBasicAuth("", self.settings.azure_pat)
        self.request_timeout = self.REQUEST_TIMEOUT_SECONDS

    @staticmethod
    def _project_ref(project: str) -> str:
        return quote(project, safe="")

    @staticmethod
    def _normalize_relation_type(relation: str) -> str:
        relation_map = {
            "System.LinkTypes.Hierarchy-Forward": "child",
            "System.LinkTypes.Hierarchy-Reverse": "parent",
            "System.LinkTypes.Related": "related",
            "Microsoft.VSTS.Common.TestedBy-Forward": "tested_by",
            "Microsoft.VSTS.Common.TestedBy-Reverse": "tests",
        }
        return relation_map.get(relation, relation)

    @staticmethod
    def _clean_text(value: str) -> str:
        text_no_tags = re.sub(r"<[^>]+>", " ", value)
        return " ".join(html.unescape(text_no_tags).split())

    @staticmethod
    def _html_to_readable_text(value: str) -> str:
        text = html.unescape(value)
        text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
        text = re.sub(r"(?i)</\s*(div|p|li|ul|ol|h1|h2|h3|h4|h5|h6)\s*>", "\n", text)
        text = re.sub(r"(?i)<\s*li\b[^>]*>", "- ", text)
        text = re.sub(
            r"(?i)</?\s*(div|p|b|strong|i|em|u|span|ul|ol|li|h1|h2|h3|h4|h5|h6|code)\b[^>]*>",
            "",
            text,
        )
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _decode_test_steps(self, steps_xml: str) -> list[dict[str, Any]]:
        try:
            root = DefusedET.fromstring(steps_xml)
        except DefusedET.ParseError:
            return []

        decoded_steps = []
        for index, step in enumerate(root.findall("step"), start=1):
            parts = step.findall("parameterizedString")
            action_raw = parts[0].text or "" if parts else ""
            expected_raw = parts[1].text or "" if len(parts) > 1 else ""

            decoded_steps.append(
                {
                    "step_number": index,
                    "step_id": int(step.get("id", "0")),
                    "step_type": step.get("type", ""),
                    "action": self._html_to_readable_text(action_raw),
                    "expected_result": self._html_to_readable_text(expected_raw),
                    "action_html": html.unescape(action_raw),
                    "expected_result_html": html.unescape(expected_raw),
                }
            )

        return decoded_steps

    def get_projects(
        self,
        top: int | None = None,
        skip: int | None = None,
        continuation_token: str | None = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/_apis/projects"
        params: dict[str, str | int] = {"api-version": "7.1"}

        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        if continuation_token:
            params["continuationToken"] = continuation_token

        response = requests.get(
            url,
            params=params,
            auth=self.auth,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_work_item(self, project: str, work_item_id: int) -> Dict[str, Any]:
        project_ref = self._project_ref(project)
        url = (
            f"{self.base_url}/{project_ref}"
            f"/_apis/wit/workitems/{work_item_id}?api-version=7.1"
        )

        response = requests.get(url, auth=self.auth, timeout=self.request_timeout)
        response.raise_for_status()
        return response.json()

    def query_by_wiql(
        self,
        project: str,
        query: str,
        top: int | None = None,
        time_precision: bool | None = None,
    ) -> Dict[str, Any]:
        project_ref = self._project_ref(project)
        url = f"{self.base_url}/{project_ref}/_apis/wit/wiql"
        params: dict[str, str | int | bool] = {"api-version": "7.1"}

        if top is not None:
            params["$top"] = top
        if time_precision is not None:
            params["timePrecision"] = time_precision

        response = requests.post(
            url,
            params=params,
            json={"query": query},
            auth=self.auth,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_work_item_with_relations(
        self, project: str, work_item_id: int
    ) -> Dict[str, Any]:
        project_ref = self._project_ref(project)
        url = (
            f"{self.base_url}/{project_ref}"
            f"/_apis/wit/workitems/{work_item_id}"
            f"?$expand=relations&api-version=7.1"
        )

        response = requests.get(url, auth=self.auth, timeout=self.request_timeout)
        response.raise_for_status()
        return response.json()

    def extract_related_ids(self, work_item: Dict[str, Any]) -> list[dict[str, Any]]:
        related_info = []
        relations = work_item.get("relations", [])

        for rel in relations:
            url = rel.get("url", "")
            if "/workItems/" not in url:
                continue

            try:
                related_id = int(url.rstrip("/").split("/")[-1])
            except ValueError:
                continue

            related_info.append(
                {
                    "id": related_id,
                    "relation": self._normalize_relation_type(rel.get("rel", "")),
                    "attributes": rel.get("attributes", {}),
                }
            )

        unique_related_info = []
        seen_ids = set()
        for info in related_info:
            if info["id"] in seen_ids:
                continue
            seen_ids.add(info["id"])
            unique_related_info.append(info)

        return unique_related_info

    def get_work_items_batch(self, project: str, ids: list[int]) -> Dict[str, Any]:
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return {"count": 0, "value": []}

        project_ref = self._project_ref(project)
        combined_ids = ",".join(str(item_id) for item_id in unique_ids)
        url = (
            f"{self.base_url}/{project_ref}"
            f"/_apis/wit/workitems?ids={combined_ids}&$expand=relations&api-version=7.1"
        )

        response = requests.get(
            url,
            auth=self.auth,
            timeout=self.request_timeout,
        )

        response.raise_for_status()
        return response.json()

    def get_related_work_items(self, project: str, work_item_id: int) -> Dict[str, Any]:
        source_item = self.get_work_item_with_relations(project, work_item_id)
        related_ids_info = self.extract_related_ids(source_item)

        if not related_ids_info:
            return {
                "work_item_id": work_item_id,
                "related_work_items": [],
            }

        batch_data = self.get_work_items_batch(
            project, [info["id"] for info in related_ids_info]
        )
        work_items_by_id = {
            item.get("id"): item for item in batch_data.get("value", [])
        }

        related_work_items = []
        for info in related_ids_info:
            related_work_items.append(
                {
                    "id": info["id"],
                    "relation": info["relation"],
                    "attributes": info["attributes"],
                    "work_item": work_items_by_id.get(info["id"]),
                }
            )

        return {
            "work_item_id": work_item_id,
            "related_work_items": related_work_items,
        }

    def get_test_workitem_steps(
        self, project: str, work_item_id: int
    ) -> Dict[str, Any]:
        work_item = self.get_work_item(project, work_item_id)
        fields = work_item.get("fields", {})
        work_item_type = fields.get("System.WorkItemType", "")

        if work_item_type != "Test Case":
            return {
                "work_item_id": work_item_id,
                "work_item_type": work_item_type,
                "message": "Work item is not a Test Case.",
                "step_count": 0,
                "test_steps": [],
            }

        steps_xml = fields.get("Microsoft.VSTS.TCM.Steps", "")
        test_steps = self._decode_test_steps(steps_xml) if steps_xml else []

        return {
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
            "title": fields.get("System.Title", ""),
            "state": fields.get("System.State", ""),
            "step_count": len(test_steps),
            "test_steps": test_steps,
        }

    def get_pull_request_by_id(
        self, project: str, pull_request_id: int
    ) -> Dict[str, Any]:
        project_ref = self._project_ref(project)
        url = (
            f"{self.base_url}/{project_ref}"
            f"/_apis/git/pullrequests/{pull_request_id}?api-version=7.1"
        )

        response = requests.get(url, auth=self.auth, timeout=self.request_timeout)
        response.raise_for_status()
        return response.json()
