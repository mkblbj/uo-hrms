import ast
import unittest
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"


def _top_level_imports(path: Path) -> set[str]:
	modules = set()
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Import):
			modules.update(alias.name.split(".")[0] for alias in node.names)
		elif isinstance(node, ast.ImportFrom) and node.module:
			modules.add(node.module.split(".")[0])
	return modules


class TestPasskeyImportIsolation(unittest.TestCase):
	"""hrms.api 在导入时就会加载 passkey 模块；webauthn 缺失时不能连带整个 hrms.api 失败。"""

	def test_passkey_modules_do_not_import_webauthn_at_module_level(self):
		for name in ("passkey.py", "passkey_webauthn.py"):
			with self.subTest(module=name):
				self.assertNotIn("webauthn", _top_level_imports(API_DIR / name))
