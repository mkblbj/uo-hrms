from pathlib import Path
import unittest


HTML_FILE = Path(__file__).resolve().parents[1] / "www" / "nfc_checkin.html"


def read_template() -> str:
	return HTML_FILE.read_text(encoding="utf-8")


class TestNfcCheckinPage(unittest.TestCase):
	def test_has_fullscreen_success_overlay_markup(self):
		html = read_template()

		self.assertIn('id="success-overlay"', html)
		self.assertIn("出勤打刻完了", html)
		self.assertIn("退勤打刻完了", html)
		self.assertIn("社員名", html)
		self.assertIn("打刻時刻", html)
		self.assertIn("打刻場所", html)

	def test_hides_card_container_on_success(self):
		html = read_template()

		self.assertIn("document.body.classList.add('success-mode')", html)
		self.assertIn("document.getElementById('success-overlay').classList.remove('hidden')", html)

	def test_extract_error_message_splits_on_escaped_newline(self):
		html = read_template()

		self.assertIn("const lines = exc.split('\\n');", html)

	def test_checkout_animation_is_moved_up_and_sped_up(self):
		html = read_template()

		self.assertIn("--coffee-speed-multiplier: 1.5;", html)
		self.assertIn("--coffee-start-delay: 1200ms;", html)
		self.assertIn("align-items: flex-start;", html)
		self.assertIn("padding-top: clamp(36px, 8vh, 96px);", html)
		self.assertIn("transform: scale(0.68);", html)
		self.assertIn(
			"animation: coffee-liquid calc(5000ms / var(--coffee-speed-multiplier)) linear calc(var(--coffee-start-delay) / var(--coffee-speed-multiplier)) infinite normal both;",
			html,
		)
		self.assertIn("6% {", html)
		self.assertIn("transform: translateY(0);", html)

	def test_success_overlay_does_not_render_employee_name_twice(self):
		html = read_template()

		self.assertNotIn('id="success-headline-name"', html)
		self.assertNotIn("const successHeadlineNameEl =", html)
		self.assertNotIn("successHeadlineNameEl.textContent = employeeName;", html)

	def test_ios_safe_area_is_covered_without_black_bars(self):
		html = read_template()

		self.assertIn("viewport-fit=cover", html)
		self.assertIn("min-height: 100dvh;", html)


if __name__ == "__main__":
	unittest.main()
