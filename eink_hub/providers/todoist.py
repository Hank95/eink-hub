"""Todoist tasks provider."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import httpx

from ..core.exceptions import ProviderError
from ..core.logging import get_logger
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.todoist")


@ProviderRegistry.register("todoist")
class TodoistProvider(BaseProvider):
    """
    Todoist tasks provider.

    Fetches:
    - Today's tasks
    - Overdue tasks
    - Upcoming tasks

    Required credentials:
    - api_token: Todoist API token

    Optional options:
    - project_filter: List of project names to include
    - priority_filter: Minimum priority (1=highest, 4=lowest)
    - max_tasks: Maximum tasks to return (default: 10)
    """

    name = "todoist"
    BASE_URL = "https://api.todoist.com/rest/v2"

    def _validate_config(self) -> None:
        """Validate Todoist config."""
        self._require_credential("api_token")

    async def fetch(self) -> ProviderData:
        """Fetch tasks from Todoist."""
        try:
            api_token = self.credentials["api_token"]

            async with httpx.AsyncClient(timeout=10.0) as client:
                tasks = await self._fetch_tasks(client, api_token)
                projects = await self._fetch_projects(client, api_token)

            project_map = {p["id"]: p["name"] for p in projects}
            processed = self._process_tasks(tasks, project_map)

            logger.info(
                f"Fetched Todoist: {len(processed['today_tasks'])} tasks today, "
                f"{len(processed['overdue_tasks'])} overdue"
            )

            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data=processed,
                ttl_seconds=600,  # 10 minutes
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Todoist API error: {e.response.status_code}")
            raise ProviderError(self.name, f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Todoist fetch failed: {e}")
            raise ProviderError(self.name, str(e))

    def get_default_refresh_interval(self) -> int:
        return 10

    async def _fetch_tasks(
        self, client: httpx.AsyncClient, api_token: str
    ) -> List[Dict[str, Any]]:
        """Fetch active tasks."""
        resp = await client.get(
            f"{self.BASE_URL}/tasks",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _fetch_projects(
        self, client: httpx.AsyncClient, api_token: str
    ) -> List[Dict[str, Any]]:
        """Fetch projects for name mapping."""
        resp = await client.get(
            f"{self.BASE_URL}/projects",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        resp.raise_for_status()
        return resp.json()

    def _process_tasks(
        self,
        tasks: List[Dict[str, Any]],
        project_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Process and categorize tasks."""
        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)

        priority_filter = self.options.get("priority_filter", 4)
        project_filter = self.options.get("project_filter", [])
        max_tasks = self.options.get("max_tasks", 10)

        today_tasks = []
        overdue_tasks = []
        upcoming_tasks = []

        for task in tasks:
            # Apply priority filter (Todoist: 1=lowest, 4=highest, we invert)
            task_priority = task.get("priority", 1)
            # Convert to our scale (1=highest)
            our_priority = 5 - task_priority
            if our_priority > priority_filter:
                continue

            # Apply project filter
            project_id = task.get("project_id")
            project_name = project_map.get(project_id, "")
            if project_filter and project_name not in project_filter:
                continue

            # Parse due date
            due = task.get("due")
            due_date = None
            due_time = None
            if due:
                due_string = due.get("date", "")
                if "T" in due_string:
                    # Has time component
                    due_dt = dt.datetime.fromisoformat(due_string.replace("Z", "+00:00"))
                    due_date = due_dt.date()
                    due_time = due_dt.strftime("%I:%M %p").lstrip("0")
                else:
                    due_date = dt.date.fromisoformat(due_string)

            task_data = {
                "id": task.get("id"),
                "title": task.get("content", "Untitled"),
                "description": task.get("description", ""),
                "priority": our_priority,
                "project": project_name,
                "due_time": due_time,
                "labels": task.get("labels", []),
            }

            if due_date:
                if due_date < today:
                    overdue_tasks.append(task_data)
                elif due_date == today:
                    today_tasks.append(task_data)
                elif due_date == tomorrow:
                    task_data["due_day"] = "Tomorrow"
                    upcoming_tasks.append(task_data)
                elif due_date <= today + dt.timedelta(days=7):
                    task_data["due_day"] = due_date.strftime("%A")
                    upcoming_tasks.append(task_data)
            else:
                # No due date - include in today's tasks
                today_tasks.append(task_data)

        # Sort by priority (higher first)
        today_tasks.sort(key=lambda t: t["priority"])
        overdue_tasks.sort(key=lambda t: t["priority"])
        upcoming_tasks.sort(key=lambda t: t["priority"])

        # Limit results
        return {
            "today_tasks": today_tasks[:max_tasks],
            "overdue_tasks": overdue_tasks[:max_tasks],
            "upcoming_tasks": upcoming_tasks[:max_tasks],
            "total_today": len(today_tasks),
            "total_overdue": len(overdue_tasks),
        }
