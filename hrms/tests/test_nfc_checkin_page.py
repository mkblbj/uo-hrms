import unittest
from pathlib import Path

HTML_FILE = Path(__file__).resolve().parents[1] / "www" / "nfc_checkin.html"
ANIMATION_TEMPLATE_FILE = (
	Path(__file__).resolve().parents[1] / "templates" / "includes" / "nfc_success_animations.html"
)
ANIMATION_CSS_FILE = (
	Path(__file__).resolve().parents[1] / "public" / "css" / "nfc_success_animations.css"
)


def read_template() -> str:
	return HTML_FILE.read_text(encoding="utf-8")


def read_optional_file(path: Path) -> str:
	if not path.exists():
		return ""
	return path.read_text(encoding="utf-8")


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
		animation_css = read_optional_file(ANIMATION_CSS_FILE)
		style_source = "\n".join([html, animation_css])

		self.assertIn("--coffee-speed-multiplier: 1.5;", style_source)
		self.assertIn("--coffee-start-delay: 1200ms;", style_source)
		self.assertIn("align-items: flex-start;", style_source)
		self.assertIn("padding-top: clamp(36px, 8vh, 96px);", style_source)
		self.assertIn("transform: scale(0.68);", style_source)
		self.assertIn(
			"animation: coffee-liquid calc(5000ms / var(--coffee-speed-multiplier)) linear calc(var(--coffee-start-delay) / var(--coffee-speed-multiplier)) infinite normal both;",
			style_source,
		)
		self.assertIn("6% {", style_source)
		self.assertIn("transform: translateY(0);", style_source)

	def test_success_overlay_does_not_render_employee_name_twice(self):
		html = read_template()

		self.assertNotIn('id="success-headline-name"', html)
		self.assertNotIn("const successHeadlineNameEl =", html)
		self.assertNotIn("successHeadlineNameEl.textContent = employeeName;", html)

	def test_success_overlay_has_random_animation_pools(self):
		html = read_template()
		animation_template = read_optional_file(ANIMATION_TEMPLATE_FILE)
		animation_css = read_optional_file(ANIMATION_CSS_FILE)

		self.assertIn(
			"const CHECKIN_SUCCESS_ANIMATIONS = ['runner', 'black-rabbit-68', 'popular-owl-27', 'empty-snail-69', 'mona-lisa'];",
			html,
		)
		self.assertIn(
			"const CHECKOUT_SUCCESS_ANIMATIONS = ['coffee', 'curvy-bulldog-27', 'wet-mayfly-23', 'kind-snail-5', 'tall-fish-38'];",
			html,
		)
		self.assertIn(
			'<link rel="stylesheet" href="/assets/hrms/css/nfc_success_animations.css">',
			html,
		)
		self.assertIn(
			'{% include "hrms/templates/includes/nfc_success_animations.html" %}',
			html,
		)
		self.assertIn("function chooseSuccessAnimationId(logType)", html)
		self.assertIn("function setSuccessAnimation(logType, animationId)", html)
		for animation_id in [
			"runner",
			"black-rabbit-68",
			"popular-owl-27",
			"empty-snail-69",
			"mona-lisa",
			"coffee",
			"curvy-bulldog-27",
			"wet-mayfly-23",
			"kind-snail-5",
			"tall-fish-38",
		]:
			self.assertIn(f'data-success-animation="{animation_id}"', animation_template)
		self.assertNotIn('data-success-animation="office-lights"', animation_template)
		self.assertNotIn('data-success-animation="work-launch"', animation_template)
		self.assertIn("https://uiverse.io/JohnnyCSilva/black-rabbit-68", animation_template)
		self.assertIn("rotate_4001510", animation_css)
		self.assertIn('class="svg_back"', animation_template)
		self.assertIn("https://uiverse.io/vinodjangid07/popular-owl-27", animation_template)
		self.assertIn('class="truckWrapper"', animation_template)
		self.assertIn("roadAnimation", animation_css)
		self.assertIn("https://uiverse.io/Nawsome/empty-snail-69", animation_template)
		self.assertIn('class="switch switch--auto-on"', animation_template)
		self.assertIn("empty-snail-auto-on", animation_css)
		self.assertIn("Uiverse.io by SelfMadeSystem", animation_template)
		self.assertIn("dashArray", animation_css)
		self.assertIn("uiverse-curvy-spin", animation_css)
		self.assertIn("wheel-and-hamster", animation_template)
		self.assertIn("capybaraloader", animation_template)
		self.assertIn('class="🤚"', animation_template)
		self.assertNotIn("https://uiverse.io/JohnnyCSilva/black-rabbit-68", html)
		self.assertNotIn('class="truckWrapper"', html)

	def test_ios_safe_area_is_covered_without_black_bars(self):
		html = read_template()

		self.assertIn("viewport-fit=cover", html)
		self.assertIn("min-height: 100dvh;", html)


if __name__ == "__main__":
	unittest.main()
