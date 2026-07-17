import ast
import unittest
from pathlib import Path


REPORT = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/report/考勤结果/考勤结果.py"


class AttendanceResultReportTest(unittest.TestCase):
	def test_source_is_initialized_before_early_exit_branch(self):
		execute = next(node for node in ast.parse(REPORT.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == "execute")
		for_node = next(node for node in ast.walk(execute) if isinstance(node, ast.For))
		assignments = [node for node in for_node.body if isinstance(node, ast.Assign)]
		source_assignments = [node for node in assignments if any(getattr(target, "id", None) == "source" for target in node.targets)]
		self.assertTrue(source_assignments, "source must be initialized in the loop body, outside conditionals")
		source_assignment = source_assignments[0]
		early_exit = next(node for node in for_node.body if isinstance(node, ast.If) and ast.unparse(node.test) == "row.early_exit")
		self.assertLess(for_node.body.index(source_assignment), for_node.body.index(early_exit))


if __name__ == "__main__":
	unittest.main()
