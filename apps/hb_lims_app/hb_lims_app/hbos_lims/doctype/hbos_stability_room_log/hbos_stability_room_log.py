# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityRoomLog(Document):
	def on_trash(self):
		"""温湿度原始记录全状态禁删（方案 8.3）。"""
		guards.guard_delete(self, "HBOS Stability Room Log", guards.ROOM_LOG_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.ROOM_LOG_SYSTEM_FIELDS)
		self._build_key()
		self._snapshot_limits()
		self._judge_within_spec()

	def _build_key(self):
		key = stb.make_room_log_key(self.room, self.log_date, self.period)
		existing = frappe.db.get_value("HBOS Stability Room Log",
									   {"room_date_period_key": key}, "name")
		if existing and existing != self.name:
			frappe.throw("该房间该日期该班次已存在温湿度记录（{}）——同房间同日期同班次仅一条（方案 5.5.2）。"
						 .format(existing))
		self.room_date_period_key = key

	def _snapshot_limits(self):
		"""上下限从 Room 快照（P1-8）；首次写入后只读。"""
		if self.get_doc_before_save() and self.temp_min is not None:
			return  # 已有快照，禁改（guard_system_fields 覆盖）
		room = frappe.db.get_value("HBOS Stability Room", self.room,
								   ["temp_min", "temp_max", "humidity_min", "humidity_max"],
								   as_dict=True)
		if not room:
			frappe.throw("稳定性房间「{}」不存在。".format(self.room))
		self.temp_min = room.temp_min
		self.temp_max = room.temp_max
		self.humidity_min = room.humidity_min
		self.humidity_max = room.humidity_max

	def _judge_within_spec(self):
		ok = True
		if self.temp_min is not None and self.temperature is not None \
				and not (float(self.temp_min) <= float(self.temperature) <= float(self.temp_max)):
			ok = False
		if self.humidity_min is not None and self.humidity is not None \
				and not (float(self.humidity_min) <= float(self.humidity) <= float(self.humidity_max)):
			ok = False
		self.within_spec = 1 if ok else 0
		if not ok and not (self.exception_desc or "").strip():
			frappe.throw("温湿度超标时必须填写异常描述（方案 5.5.2）。")
