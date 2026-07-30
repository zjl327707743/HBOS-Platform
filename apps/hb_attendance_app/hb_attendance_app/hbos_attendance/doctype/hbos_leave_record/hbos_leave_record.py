import frappe
from frappe.model.document import Document


class HBOSLeaveRecord(Document):
    """HBOS Leave Record — stores leave/absence records synced from Feishu approval system."""

    def before_save(self):
        self._calculate_leave_days()

    def _calculate_leave_days(self):
        """Auto-calculate leave days from start/end dates."""
        if self.start_date and self.end_date:
            from datetime import date, timedelta
            d = self.start_date if isinstance(self.start_date, date) else date.fromisoformat(str(self.start_date))
            end = self.end_date if isinstance(self.end_date, date) else date.fromisoformat(str(self.end_date))
            days = 0
            while d <= end:
                days += 1
                d += timedelta(days=1)
            self.leave_days = days