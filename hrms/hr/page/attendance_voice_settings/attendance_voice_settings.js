frappe.pages["attendance-voice-settings"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "考勤语音设置",
		single_column: true,
	});
	wrapper.voice_settings = new frappe.AttendanceVoiceSettings(page);
};
frappe.pages["attendance-voice-settings"].on_page_show = function (wrapper) {
	if (wrapper.voice_settings) wrapper.voice_settings.resume();
};

frappe.AttendanceVoiceSettings = class {
	constructor(page) {
		this.page = page;
		this.root = document.createElement("div");
		this.root.className = "voice-settings";
		page.main.append(this.root);
		this.catalog = [];
		this.busy = false;
		this.dirty = false;
		this.root.innerHTML = `<style>
   .voice-settings{padding:24px;max-width:1440px;margin:auto;color:var(--text-color)}
   .voice-settings h2{font-size:20px;margin:0 0 8px}.voice-settings p{margin:0;line-height:1.6}
   .voice-settings .vs-muted{color:var(--text-muted);font-size:13px}.voice-settings .vs-grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,1fr);gap:20px;margin:20px 0}
   .voice-settings .vs-card{background:var(--fg-color);border:1px solid var(--border-color);border-radius:12px;padding:20px}
   .voice-settings .vs-card h3{font-size:16px;margin:0 0 16px}.voice-settings .vs-fields{display:grid;grid-template-columns:1fr 1fr;gap:16px}
   .voice-settings label{display:block;font-weight:500;font-size:13px;margin-bottom:6px}.voice-settings .form-control{height:40px}
   .voice-settings .vs-full{grid-column:1/-1}.voice-settings .vs-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:18px}
   .voice-settings button{min-height:38px}.voice-settings button:focus-visible,.voice-settings input:focus-visible,.voice-settings select:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
   .voice-settings .vs-status{border-left:3px solid var(--primary);padding:8px 12px;background:var(--subtle-fg);margin-top:14px;font-size:13px;line-height:1.6}
   .voice-settings .vs-error{color:var(--red-600);background:var(--red-50);border-radius:8px;padding:12px;margin-top:14px;white-space:pre-wrap}
   .voice-settings .vs-toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:14px}
   .voice-settings .vs-toolbar input{max-width:320px}.voice-settings table{width:100%;border-collapse:collapse}
   .voice-settings th{text-align:left;background:var(--subtle-fg);font-size:13px;padding:12px;font-weight:500}
   .voice-settings td{padding:12px;border-bottom:1px solid var(--border-color);vertical-align:middle}
   .voice-settings .vs-employee{font-weight:500}.voice-settings .vs-id{font-size:12px;color:var(--text-muted);margin-top:4px}
   .voice-settings .vs-preview-buttons{display:flex;gap:8px}.voice-settings audio{width:100%;margin:12px 0}
   .voice-settings .vs-preview-text{font-size:15px;line-height:1.7;min-height:56px;word-break:break-word}
   .voice-settings progress{width:100%;height:10px;accent-color:var(--primary);margin-top:12px}
   .voice-settings [hidden]{display:none!important}.voice-settings .vs-empty{text-align:center;padding:28px;color:var(--text-muted)}
   @media(max-width:767px){.voice-settings{padding:12px}.voice-settings .vs-grid{grid-template-columns:1fr;gap:12px;margin:14px 0}.voice-settings .vs-card{padding:16px}.voice-settings .vs-fields{grid-template-columns:1fr}.voice-settings .vs-toolbar{align-items:stretch;flex-direction:column}.voice-settings .vs-toolbar input{max-width:none}.voice-settings table,.voice-settings tbody,.voice-settings tr,.voice-settings td{display:block}.voice-settings thead{display:none}.voice-settings tr{padding:12px 0;border-bottom:1px solid var(--border-color)}.voice-settings td{border:0;padding:6px 0}.voice-settings td[data-label]:before{content:attr(data-label);display:block;font-size:12px;color:var(--text-muted);margin-bottom:5px}.voice-settings button{min-height:44px}.voice-settings .vs-actions button{flex:1}}
  </style>
  <h2>让签到牌叫对每个人的姓</h2><p class="vs-muted">改好姓氏读音，选一个喜欢的声音。试听满意后生成，最后发布到签到牌。</p>
  <div class="vs-status" data-id="published" role="status">正在读取已发布语音…</div>
  <div class="vs-error" data-id="error" role="alert" hidden></div>
  <div class="vs-grid">
   <section class="vs-card" aria-label="声音设置"><h3>声音设置</h3>
    <div class="vs-fields">
     <div><label for="vs-engine">声音类型</label><select id="vs-engine" class="form-control"><option value="voicevox">VOICEVOX · 角色音色</option><option value="nemo">Nemo · 通用音色</option></select></div>
     <div><label for="vs-speed">语速</label><input id="vs-speed" class="form-control" type="number" min="0.5" max="2" step="0.05" value="1"></div>
     <div><label for="vs-speaker">角色 / 说话人</label><select id="vs-speaker" class="form-control" disabled><option>请先加载音色</option></select></div>
     <div><label for="vs-style">说话风格</label><select id="vs-style" class="form-control" disabled><option>请先加载音色</option></select></div>
     <div class="vs-full"><button class="btn btn-default btn-sm" data-action="voices">加载音色</button><span class="vs-muted" data-id="voice-credit" style="margin-left:10px">首次加载可能需要一点时间</span></div>
    </div>
    <div class="vs-actions"><button class="btn btn-default" data-action="save">保存草稿</button><button class="btn btn-primary" data-action="generate">生成全员语音</button><button class="btn btn-primary" data-action="publish" disabled>发布到签到牌</button></div>
    <div class="vs-status" data-id="job" role="status">尚未生成新的语音。保存或试听不会更改当前声音。</div><progress data-id="progress" value="0" max="1" hidden aria-label="语音生成进度"></progress>
   </section>
   <section class="vs-card" aria-label="试听"><h3>试听</h3><p class="vs-preview-text" data-id="preview-text">在下方选择员工，点击“试听签到”或“试听签退”。</p>
    <audio controls preload="none" data-id="audio" aria-label="语音试听播放器"></audio><p class="vs-muted" data-id="preview-credit"></p>
    <div class="vs-status">签到：姓氏さん、おはようございます。<br>签退：姓氏さん、お疲れさまでした。</div>
   </section>
  </div>
  <section class="vs-card"><div class="vs-toolbar"><div><h3 style="margin-bottom:4px">员工姓氏读音</h3><p class="vs-muted">只填姓的假名，例如 ワン；不填名字或“さん”。留空时按自动姓氏读音生成。</p></div><input class="form-control" data-id="search" aria-label="搜索员工" placeholder="搜索姓名或员工编号"></div>
   <table><thead><tr><th>员工</th><th>自动姓氏</th><th>姓氏读音（假名）</th><th>试听</th></tr></thead><tbody data-id="employees"></tbody></table>
  </section>`;
		this.root.addEventListener("click", (e) => {
			const b = e.target.closest("[data-action]");
			if (b) this.action(b.dataset.action, b);
		});
		this.root.addEventListener("input", (e) => {
			if (e.target.matches("[data-employee]")) {
				this.draft.readings[e.target.dataset.employee] = e.target.value;
				this.changed();
			} else if (e.target.id === "vs-speed") {
				this.draft.speed = Number(e.target.value);
				this.changed();
			} else if (e.target === this.el("search")) this.rows();
		});
		this.root.querySelector("#vs-engine").addEventListener("change", (e) => {
			this.draft.engine = e.target.value;
			this.catalog = [];
			this.changed();
			this.voices();
		});
		this.root.querySelector("#vs-speaker").addEventListener("change", () => this.styles(true));
		this.root.querySelector("#vs-style").addEventListener("change", (e) => {
			this.draft.speaker_id = Number(e.target.value);
			this.changed();
			this.credit();
		});
		this.load();
	}
	el(id) {
		return this.root.querySelector(`[data-id="${id}"]`);
	}
	escape(value) {
		return String(value ?? "").replace(
			/[&<>"']/g,
			(c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
		);
	}
	async call(method, args = {}) {
		const r = await frappe.call({
			method: "hrms.api.attendance_voice_settings." + method,
			args,
			error: () => {},
		});
		return r.message;
	}
	error(error) {
		let msg = error?.responseJSON?.exception || error?.message || "操作未完成，请稍后重试";
		msg = String(msg).replace(/^[\w.]+(?:Error|Exception):\s*/, "");
		this.el("error").textContent = msg;
		this.el("error").hidden = false;
	}
	changed() {
		this.dirty = true;
		this.status();
	}
	status() {
		const generation = this.state?.generation;
		const running = ["queued", "running"].includes(generation?.status);
		const source = this.state?.published?.source || {};
		this.el("published").textContent = `当前已发布：${source.voice || "暂无语音"} · ${
			this.state?.published?.employees || 0
		} 人${this.dirty ? "　｜　有未保存的修改" : ""}`;
		this.el("job").textContent = running
			? `正在生成 ${generation.done || 0} / ${
					generation.total
			  } 段，请稍候。当前签到牌继续使用原有声音。`
			: generation?.status === "ready"
			  ? generation.can_publish && !this.dirty
					? "语音已生成，点击“发布到签到牌”后生效。"
					: "草稿或员工资料已变化，请保存并重新生成。"
			  : generation?.status === "published"
			    ? "已发布，签到牌下次打卡会使用新语音。"
			    : generation?.status === "error"
			      ? generation.error
			      : "尚未生成新的语音。保存或试听不会更改当前声音。";
		this.el("progress").hidden = !running;
		this.el("progress").max = generation?.total || 1;
		this.el("progress").value = generation?.done || 0;
		this.root.querySelectorAll("button[data-action]").forEach((b) => {
			b.disabled =
				this.busy || (running && ["generate", "preview"].includes(b.dataset.action));
		});
		this.root.querySelector('[data-action="publish"]').disabled =
			this.busy || this.dirty || !generation?.can_publish;
		this.root.querySelectorAll("#vs-engine,#vs-speed,[data-employee]").forEach((input) => {
			input.disabled = this.busy;
		});
		this.root.querySelectorAll("#vs-speaker,#vs-style").forEach((select) => {
			select.disabled = this.busy || !this.catalog.length;
		});
	}
	async load() {
		try {
			this.state = await this.call("get_settings");
			this.draft = JSON.parse(JSON.stringify(this.state.draft));
			this.dirty = false;
			this.root.querySelector("#vs-engine").value = this.draft.engine;
			this.root.querySelector("#vs-speed").value = this.draft.speed;
			this.rows();
			this.status();
			this.resume();
		} catch (e) {
			this.error(e);
		}
	}
	rows() {
		if (!this.state) return;
		const filter = this.el("search").value.trim().toLowerCase();
		const employees = this.state.employees.filter((e) =>
			(e.employee_name + e.name).toLowerCase().includes(filter),
		);
		this.el("employees").innerHTML =
			employees
				.map(
					(e) =>
						`<tr><td><div class="vs-employee">${this.escape(
							e.employee_name,
						)}</div><div class="vs-id">${this.escape(
							e.name,
						)}</div></td><td data-label="自动姓氏">${this.escape(
							e.surname,
						)}</td><td data-label="姓氏读音（假名）"><input class="form-control" data-employee="${this.escape(
							e.name,
						)}" aria-label="${this.escape(
							e.employee_name,
						)}的姓氏读音" value="${this.escape(
							this.draft.readings[e.name] || "",
						)}" placeholder="默认：${this.escape(
							e.surname,
						)}"></td><td><div class="vs-preview-buttons"><button class="btn btn-default btn-sm" data-action="preview" data-person="${this.escape(
							e.name,
						)}" data-kind="IN">试听签到</button><button class="btn btn-default btn-sm" data-action="preview" data-person="${this.escape(
							e.name,
						)}" data-kind="OUT">试听签退</button></div></td></tr>`,
				)
				.join("") || '<tr><td class="vs-empty" colspan="4">没有匹配的员工</td></tr>';
		this.status();
	}
	styleName(name) {
		return (
			{
				ノーマル: "自然",
				あまあま: "温柔",
				ツンツン: "傲娇",
				セクシー: "成熟",
				ささやき: "轻声",
				ヒソヒソ: "耳语",
				喜び: "开心",
				怒り: "生气",
				悲しみ: "悲伤",
				クイーン: "女王",
			}[name] || name
		);
	}
	async voices() {
		try {
			this.busy = true;
			this.status();
			this.el("voice-credit").textContent = "正在准备音色，请稍候…";
			this.catalog = await this.call("get_voices", { engine: this.draft.engine });
			const speaker = this.root.querySelector("#vs-speaker");
			speaker.innerHTML = [...new Set(this.catalog.map((v) => v.name))]
				.map((n) => `<option value="${this.escape(n)}">${this.escape(n)}</option>`)
				.join("");
			speaker.disabled = false;
			const current = this.catalog.find((v) => v.id === Number(this.draft.speaker_id));
			speaker.value = current?.name || this.catalog[0]?.name;
			this.styles(!current);
		} catch (e) {
			this.el("voice-credit").textContent = "音色加载未完成，可稍后重试";
			this.error(e);
		} finally {
			this.busy = false;
			this.status();
		}
	}
	styles(change) {
		const selected = this.root.querySelector("#vs-speaker").value;
		const options = this.catalog.filter((v) => v.name === selected);
		const style = this.root.querySelector("#vs-style");
		style.innerHTML = options
			.map((v) => `<option value="${v.id}">${this.escape(this.styleName(v.style))}</option>`)
			.join("");
		style.disabled = false;
		if (options.some((v) => v.id === Number(this.draft.speaker_id)))
			style.value = this.draft.speaker_id;
		else this.draft.speaker_id = Number(style.value);
		if (change) {
			this.draft.speaker_id = Number(style.value);
			this.changed();
		}
		this.credit();
	}
	credit() {
		const voice = this.catalog.find((v) => v.id === Number(this.draft.speaker_id));
		this.el("voice-credit").textContent = voice ? "音声来源：" + voice.credit : "请选择音色";
	}
	async save() {
		this.state = await this.call("save_settings", {
			config: JSON.stringify(this.draft),
			revision: this.state.revision,
		});
		this.dirty = false;
		this.status();
	}
	async action(action, button) {
		if (this.busy || !this.state) return;
		this.el("error").hidden = true;
		if (action === "voices") return this.voices();
		try {
			this.busy = true;
			this.status();
			if (action === "save") {
				await this.save();
				frappe.show_alert({ message: "草稿已保存，当前声音未改变", indicator: "green" });
			}
			if (action === "preview") {
				this.el("preview-text").textContent = "正在准备试听，请稍候…";
				const result = await this.call("preview", {
					config: JSON.stringify(this.draft),
					employee_id: button.dataset.person,
					kind: button.dataset.kind,
				});
				this.el("preview-text").textContent = result.text;
				this.el("preview-credit").textContent = "音声来源：" + result.credit;
				this.el("audio").src = result.url;
				this.el("audio")
					.play()
					.catch(() => {
						this.el("preview-credit").textContent += " · 请点击播放器播放";
					});
			}
			if (action === "generate") {
				if (this.dirty) await this.save();
				await this.call("start_generation", { revision: this.state.revision });
				await this.poll();
			}
			if (action === "publish") {
				this.state = await this.call("publish", { request_id: this.state.generation.id });
				frappe.show_alert({ message: "已发布到签到牌", indicator: "green" });
			}
		} catch (e) {
			this.error(e);
		} finally {
			this.busy = false;
			this.status();
			this.resume();
		}
	}
	async poll() {
		try {
			const fresh = await this.call("get_settings");
			this.state.generation = fresh.generation;
			this.state.published = fresh.published;
			this.status();
			if (!["queued", "running"].includes(fresh.generation?.status))
				clearInterval(this.timer);
		} catch (e) {
			this.error(e);
		}
	}
	resume() {
		clearInterval(this.timer);
		if (this.state && ["queued", "running"].includes(this.state.generation?.status)) {
			this.timer = setInterval(() => {
				if (frappe.get_route()[0] !== "attendance-voice-settings") {
					clearInterval(this.timer);
					return;
				}
				this.poll();
			}, 2000);
		}
	}
};
