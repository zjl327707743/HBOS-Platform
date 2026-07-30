import frappe
from frappe.model.document import Document


class HBOSOvertimeRecord(Document):
    """HBOS Overtime Record — stores overtime records synced from Feishu approval system."""

    def before_save(self):
        self._calculate_duration()

    def _calculate_duration(self):
        """Auto-calculate overtime duration from start/end times."""
        if self.start_time and self.end_time:
            if isinstance(self.start_time, str):
                from datetime import datetime
                start = datetime.fromisoformat(self.start_time)
                end = datetime.fromisoformat(self.end_time)
                diff = (end - start).total_seconds() / 3600
                self.duration_hours = round(diff, 1)