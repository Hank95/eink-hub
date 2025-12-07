"""Todoist tasks widget."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("todoist")
class TodoistWidget(BaseWidget):
    """
    Todoist tasks display widget.

    Shows today's tasks and optionally overdue tasks.

    Options:
    - max_tasks: int (default: 5)
    - show_overdue: bool (default: True)
    - show_priority: bool (default: True) - Show priority indicator
    - show_project: bool (default: False) - Show project name
    - compact: bool (default: False) - Single line per task
    """

    name = "todoist"

    # Priority indicators (1=highest priority)
    PRIORITY_MARKERS = {
        1: "!!!",
        2: "!!",
        3: "!",
        4: "",
    }

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render todoist tasks."""
        if not data:
            self._render_no_data(draw, "No tasks data")
            return

        max_tasks = self.options.get("max_tasks", 5)
        show_overdue = self.options.get("show_overdue", True)
        show_priority = self.options.get("show_priority", True)
        show_project = self.options.get("show_project", False)
        compact = self.options.get("compact", False)

        today_tasks = data.get("today_tasks", [])
        overdue_tasks = data.get("overdue_tasks", [])

        title_font = self._load_font(14, bold=True)
        task_font = self._load_font(13)
        detail_font = self._load_font(11)

        y = self.bounds.y
        tasks_shown = 0

        # Overdue tasks (if any)
        if show_overdue and overdue_tasks:
            draw.text((self.bounds.x, y), "Overdue", font=title_font, fill=0)
            y += 18

            for task in overdue_tasks:
                if tasks_shown >= max_tasks:
                    break
                y = self._render_task(
                    draw, task, y, task_font, detail_font,
                    show_priority, show_project, compact, is_overdue=True
                )
                tasks_shown += 1

            y += 6  # Spacing

        # Today's tasks
        if today_tasks and tasks_shown < max_tasks:
            remaining = max_tasks - tasks_shown
            header = "Today" if show_overdue and overdue_tasks else "Tasks"
            draw.text((self.bounds.x, y), header, font=title_font, fill=0)
            y += 18

            for task in today_tasks[:remaining]:
                y = self._render_task(
                    draw, task, y, task_font, detail_font,
                    show_priority, show_project, compact, is_overdue=False
                )

        # No tasks message
        if not today_tasks and not overdue_tasks:
            msg_font = self._load_font(14)
            draw.text(
                (self.bounds.x, self.bounds.y + 20),
                "All tasks complete!",
                font=msg_font,
                fill=128,
            )

    def _render_task(
        self,
        draw: ImageDraw.ImageDraw,
        task: Dict[str, Any],
        y: int,
        task_font,
        detail_font,
        show_priority: bool,
        show_project: bool,
        compact: bool,
        is_overdue: bool,
    ) -> int:
        """
        Render a single task.

        Returns the new y position after rendering.
        """
        x = self.bounds.x
        max_width = self.bounds.width

        title = task.get("title", "Untitled")
        priority = task.get("priority", 4)
        project = task.get("project", "")
        due_time = task.get("due_time", "")

        # Build task line
        prefix = ""
        if show_priority and priority <= 3:
            prefix = self.PRIORITY_MARKERS.get(priority, "") + " "

        # Checkbox indicator
        checkbox = "○ "
        task_text = checkbox + prefix + title

        # Truncate if needed
        task_text = self._truncate_text(draw, task_text, task_font, max_width)

        # Draw with different color if overdue
        fill = 0
        draw.text((x, y), task_text, font=task_font, fill=fill)
        y += 17

        # Details line (if not compact)
        if not compact and (show_project or due_time):
            details = []
            if due_time:
                details.append(due_time)
            if show_project and project:
                details.append(project)

            if details:
                detail_text = "  •  ".join(details)
                detail_text = self._truncate_text(
                    draw, detail_text, detail_font, max_width - 15
                )
                draw.text((x + 15, y), detail_text, font=detail_font, fill=128)
                y += 14

        return y

    def get_required_provider(self) -> Optional[str]:
        return "todoist"
