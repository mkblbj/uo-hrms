import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
	sys.path.insert(0, str(APP_ROOT))

QR_ATTENDANCE_FILE = APP_ROOT / "hrms" / "api" / "qr_attendance.py"
PASSKEY_FILE = APP_ROOT / "hrms" / "api" / "passkey.py"
COOLDOWN_FILE = APP_ROOT / "hrms" / "api" / "checkin_cooldown.py"


def read_source(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def load_cooldown_module():
	spec = spec_from_file_location("checkin_cooldown", COOLDOWN_FILE)
	module = module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class TestCheckinCooldownExemption(unittest.TestCase):
	def test_only_employee_44_is_exempt_from_checkin_cooldowns(self):
		cooldown = load_cooldown_module()

		self.assertTrue(cooldown.is_checkin_cooldown_exempt("44"))
		self.assertFalse(cooldown.is_checkin_cooldown_exempt("45"))
		self.assertFalse(cooldown.is_checkin_cooldown_exempt(""))
		self.assertFalse(cooldown.is_checkin_cooldown_exempt(None))

	def test_qr_checkin_cooldowns_are_guarded_by_employee_exemption(self):
		source = read_source(QR_ATTENDANCE_FILE)

		self.assertIn(
			"from hrms.api.checkin_cooldown import is_checkin_cooldown_exempt",
			source,
		)
		guarded_block = source.split("if not is_checkin_cooldown_exempt(employee):", 1)[1].split(
			"# 8. 地理位置验证",
			1,
		)[0]

		self.assertIn("Please wait at least 15 minutes before checking out", guarded_block)
		self.assertIn("Please wait at least 5 minutes before checking in", guarded_block)
		self.assertIn("within the last 5 minutes", guarded_block)

	def test_passkey_checkin_cooldown_is_guarded_by_employee_exemption(self):
		source = read_source(PASSKEY_FILE)

		self.assertIn(
			"from hrms.api.checkin_cooldown import is_checkin_cooldown_exempt",
			source,
		)
		guarded_block = source.split("if not is_checkin_cooldown_exempt(employee):", 1)[1].split(
			"# 创建 Employee Checkin",
			1,
		)[0]

		self.assertIn("recent_checkin", guarded_block)
		self.assertIn("within the last 5 minutes", guarded_block)


if __name__ == "__main__":
	unittest.main()
